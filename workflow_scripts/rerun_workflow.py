#!/usr/bin/env python

import os
import subprocess
import json
import yaml
from vasp_run import vasp
from pymatgen.io.vasp.inputs import Incar
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.vasp.outputs import Vasprun

def check_path_exists(path):
    # called in check_vasp_input, among others
    if os.path.exists(path):
        return True
    else:
        return False

def check_vasp_input(path):
    # called in check_num_jobs_in_workflow
    incar = os.path.join(path, 'INCAR')
    kpoints = os.path.join(path, 'KPOINTS')
    potcar = os.path.join(path, 'POTCAR')
    poscar = os.path.join(path, 'POSCAR')
    if check_path_exists(incar) and check_path_exists(kpoints) and check_path_exists(potcar) and check_path_exists(poscar):
        return True
    else:
        return False

def check_num_jobs_in_workflow(pwd):
    # called in driver
    num_jobs = 0
    for root, dirs, files in os.walk(pwd):
        for file in files:
            if file == 'POTCAR' and check_vasp_input(root) == True:
                num_jobs +=1
    return num_jobs

def get_incar_value(path, tag):
    # called in get_job_name
    incar = Incar.from_file(os.path.join(path,'INCAR'))
    value = incar[tag]
    return value

def default_naming(path):
    # called in get_job_name
    struct = Poscar.from_file(os.path.join(path,'POSCAR')).structure
    formula = str(struct.composition.formula).replace(' ', '')
    directories = path.split(os.sep)

    return formula + '-' + directories[-2] + '-' + directories[-1]

def replace_incar_tags(path, tag, value):
    # called in get_job_name
    incar = Incar.from_file(os.path.join(path, 'INCAR'))
    incar.__setitem__(tag, value)
    incar.write_file(os.path.join(path, 'INCAR'))

def get_job_name(path):
    # called in get_single_job_name
    if 'SYSTEM' in open(os.path.join(path, 'INCAR')).read():
        name = get_incar_value(path, 'SYSTEM')
        return str(name)
    else:
        name = default_naming(path)
        replace_incar_tags(path, 'SYSTEM', name)
        return str(name)

def get_single_job_name(pwd):
    # called in driver
    for root, dirs, files in os.walk(pwd):
        for file in files:
            if file == 'POTCAR' and check_vasp_input(root) == True:
                job_name = get_job_name(root)
    return job_name

def jobs_in_queue():
    # called in not_in_queue
    p = subprocess.Popen(['squeue' ,'-o', '"%Z %T"'], stdout=subprocess.PIPE)
    #can be user specific, add -u username
    jobs_running = []
    line_count = 0
    for line in p.stdout:
        if line_count > 0:
            line = str(line, 'utf-8').replace('"', '').split()
            jobs_running.append((line[0], line[1])) # tuple is (directory, status)
        line_count += 1
    all_jobs_dict = {job[0]:job[1] for job in jobs_running}
    return all_jobs_dict

def not_in_queue(path):
    # called in vasp_run_main
    all_jobs_dict = jobs_in_queue()

    if path not in all_jobs_dict:
        return True
    elif all_jobs_dict[path] == 'COMPLETING' or all_jobs_dict[path] == 'COMPLETED':
        return True
    else:
        return all_jobs_dict[path]

def is_converged(path):
    # called in vasp_run_main
    job_name = get_job_name(path)
    rerun = False
    if not_in_queue(path) == True:  # Continue if job is not in queue
        if 'STAGE_NUMBER' in open(os.path.join(path, 'INCAR')).read():
            if os.path.exists(os.path.join(path, 'CONVERGENCE')):
                with open('CONVERGENCE') as fd:
                    pairs = (line.split(None) for line in fd)
                    res   = {int(pair[0]):pair[1] for pair in pairs if len(pair) == 2 and pair[0].isdigit()}
                    max_stage_number = len(res) - 1
                    fd.close()
            else:
                raise Exception('Copy CONVERGENCE file into execution directory \
                                 to run multistep job. Delete STAGE_NUMBER tag \
                                 from INCAR for single step job.')

            current_stage_number = get_incar_value(path, 'STAGE_NUMBER')
            if current_stage_number < max_stage_number:
                rerun = 'multi'    #RERUN JOB
                print('Rerunning ' + job_name + ' stage ' + str(current_stage_number) + ' of ' + str(max_stage_number))
            elif current_stage_number == max_stage_number:
                V = Vasprun(os.path.join(path, 'vasprun.xml'))
                if V.converged != True:
                    if V.converged_electronic != True:
                        replace_incar_tags(path, 'NELM', 500) #increase number of electronic steps
                        print('Increased NELM to 500 max steps for electronic convergence.')
                        rerun = 'multi'  #RERUN JOB
                    elif V.converged_ionic != True and int(get_incar_value(path, 'NSW')) == 0:
                        print(job_name + ' Assuming you do not want to resubmit job! Single point energy calculation: converged_electronic = TRUE, converged_ionic = FALSE')
                        rerun = 'converged'
                    else:
                        print('Rerunning ' + job_name + ' stage ' + str(current_stage_number) + ' of ' + str(max_stage_number))
                        rerun = 'multi'  #RERUN JOB    Catch-all for all other errors
                else:
                    print(job_name + ' Complete and ready for post processing.') #Job complete. Can perform post processing (bader lobster bandstructure defects adsorbates etc.)
                    rerun = 'converged'
            elif 'IMAGES' in open(os.path.join(path,'INCAR')).read():
                print('DOES NOT HANDLE NEB YET')
            else:
                V = Vasprun(os.path.join(path, 'vasprun.xml'))
                if V.converged != True:        #Job not converge
                    if V.converged_electronic != True:
                        replace_incar_tags(path, 'NELM', 500) #increase number of electronic steps
                        print('Increased NELM to 500 max steps for electronic convergence.')
                        rerun = 'single'  #RERUN JOB
                    elif V.converged_ionic != True and int(get_incar_value(path, 'NSW')) == 0:
                        print(job_name + ' Assuming you do not want to resubmit job!! Single point energy calculation: converged_electronic = TRUE, converged_ionic = FALSE')
                        rerun = 'converged'
                    else:
                        rerun = 'single'  #RERUN JOB    Catch-all for all other errors
                else:
                    print(job_name + ' Complete and ready for post processing.') #Job has completed #post processing bader lobster bandstructure ect...
                    rerun = 'converged'

            return rerun

def rerun_job(job_type, job_name):
    # called in vasp_run_main. Requires vasp.py to be in path
    vasp_path = os.path.abspath(vasp.__file__)
    if job_type == 'multi':
        os.system(vasp_path + ' -m CONVERGENCE -n ' + job_name)
    if job_type == 'single':
        os.system(vasp_path + ' -n ' + job_name)
    if job_type == 'multi_initial':
        os.system(vasp_path + ' -m CONVERGENCE --init -n ' + job_name)

def store_data(vasprun_obj, job_name):
    # called in vasp_run_main
    entry_obj = vasprun_obj.as_dict()
    entry_obj["complete_dos"] = vasprun_obj.complete_dos.as_dict()
    entry_obj["entry_id"] = job_name

    return entry_obj

def fizzled_job(path):
    job_name = get_job_name(path)
    rerun = False
    if not_in_queue(path) == True: # Continue if job is not in queue
        if 'STAGE_NUMBER' in open(os.path.join(path, 'INCAR')).read():
            if check_path_exists(os.path.join(path, 'CONVERGENCE')):
                with open('CONVERGENCE') as fd:
                    pairs = (line.split(None) for line in fd)
                    res   = {int(pair[0]):pair[1] for pair in pairs if len(pair) == 2 and pair[0].isdigit()}
                    max_stage_number = len(res) - 1
                    fd.close()
            else:
                raise Exception('Copy CONVERGENCE file into execution directory to run multistep job. Delete STAGE_NUMBER tag from INCAR for single step job.')

            current_stage_number = get_incar_value(path, 'STAGE_NUMBER')
            rerun = 'multi'
        else:
            rerun = 'single'

    return rerun

def vasp_run_main(pwd):
    # called in driver
    completed_jobs = {'PATHs': {}}
    computed_entries = []
    for root, dirs, files in os.walk(pwd):
        for file in files:
            if file == 'POTCAR':
                if check_vasp_input(root) == True:
                    print('#********************************************#\n')
                    job_name = get_job_name(root)
                    if not_in_queue(root) == True:
                        if check_path_exists(os.path.join(root, 'vasprun.xml')):
                            try:
                                V = Vasprun(os.path.join(root, 'vasprun.xml'))
                                fizzled = False
                            except:
                                print(root, '  Fizzled job, check errors! Attempting to resubmit...')
                                fizzled = True
                            if fizzled == False:
                                os.chdir(root)
                                job = is_converged(root)
                                rerun_job(job, job_name)
                                if job == 'converged':
                                    completed_jobs['PATHs'][str(root)] = str(job_name)
                                    store_dict = store_data(V, job_name)
                                    computed_entries.append(store_dict)
                                else:
                                    pass
                            else:
                                os.chdir(root)
                                job = fizzled_job(root)
                                rerun_job(job, job_name)
                        elif check_path_exists(os.path.join(root, 'CONVERGENCE')):
                            print(job_name + ' Initializing multi-step run.')
                            os.chdir(root)
                            rerun_job('multi_initial', job_name)
                        else:
                            print(job_name + ' Initializing run.')
                            os.chdir(root)
                            rerun_job('single', job_name)
                    else:
                        print(job_name + ' Job in queue. Status: ' + not_in_queue(root))
                    print('\n')

    num_jobs_in_workflow = check_num_jobs_in_workflow(pwd)
    if num_jobs_in_workflow > 1:
        if not completed_jobs:
            pass
        else:
            with open(os.path.join(pwd, 'completed_jobs.yml'), 'w') as outfile:
                yaml.dump(completed_jobs, outfile, default_flow_style=False)

        if len(list(completed_jobs['PATHs'].keys())) == num_jobs_in_workflow:
            print('\n  ALL JOBS HAVE CONVERGED!  \n')
            with open(os.path.join(pwd, 'WORKFLOW_CONVERGENCE'), 'w') as f:
                f.write('WORKFLOW_CONVERGED = True')
                f.close()

    return computed_entries

def driver():
    pwd = os.getcwd()
    num_jobs_in_workflow = check_num_jobs_in_workflow(pwd)

    with open(os.path.join(pwd, 'WORKFLOW_CONVERGENCE'), 'w') as f:
        f.write('WORKFLOW_CONVERGED = False')
        f.close()

    if num_jobs_in_workflow > 1:
        if check_path_exists(os.path.join(pwd, 'WORKFLOW_NAME')):
            workflow_file = Incar.from_file(os.path.join(pwd, 'WORKFLOW_NAME'))
            workflow_name = workflow_file['NAME']
        else:
            print('\n#---------------------------------#\n')
            workflow_name = input("Please enter a name for this workflow: ")
            print('\n#---------------------------------#\n')

            with open(os.path.join(pwd, 'WORKFLOW_NAME'), 'w') as f:
                writeline = 'NAME = ' + str(workflow_name)
                f.write(writeline)
                f.close()
    else:
        workflow_name = get_single_job_name(pwd)

    # need dependencies for vasp_run_main
    computed_entries = vasp_run_main(pwd)
    if computed_entries is None:
        pass
    else:
        with open(os.path.join(pwd, str(workflow_name) + '_converged.json'), 'w') as f:
            json.dump(computed_entries, f)

if __name__ == '__main__':
    driver()
