{% extends "VASP.base.jinja2.sh" %}
{% block python %}
from custodian.custodian import *
from Classes_Custodian import *
import Upgrade_Run
import logging
import copy

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, filename='run.log')
jobtype = '{{ jobtype }}'
vasp_kpts = '{{ vasp_kpts }}'
vasp_gamma =  '{{ vasp_gamma }}'
vasp_ncl = '{{ vasp_ncl }}'

if jobtype == 'NEB':
    handlers = [NEBWalltimeHandler({{ time }}*60*60, min(30*60, {{ time }}*60*60/20), electronic_step_stop=True)]
    job = NEBJob
    images = Incar.from_file('INCAR')['IMAGES']
    continuation = []
    for i in range(1, images+1):
        folder = str(i).zfill(2)
        continuation.append({'file': os.path.join(folder, 'CONTCAR'),
                             'action': {'_file_copy': {'dest': os.path.join(folder, 'POSCAR')}}})
elif jobtype == 'Dimer':
    handlers = [WalltimeHandler({{ time }}*60*60, min(30*60, {{ time }}*60*60/20), electronic_step_stop=True),
                DimerDivergingHandler()]
    job = DimerJob
    continuation = [{'file': 'CONTCAR',
                     'action': {'_file_copy': {'dest': 'POSCAR'}}},
                    {'file': 'NEWMODECAR',
                     'action' : {'_file_copy': {'dest': 'MODECAR'}}}]
elif jobtype == 'Standard':
    handlers = [WalltimeHandler({{ time }}*60*60, min(30*60, {{ time }}*60*60/20), electronic_step_stop=True)]
    job = StandardJob
    continuation = [{'file': 'CONTCAR',
                     'action': {'_file_copy': {'dest': 'POSCAR'}}}]


def get_runs(max_steps=100):
    for i in range(max_steps):
        if i > 0 and ((not os.path.exists('CONTCAR') or os.path.getsize('CONTCAR') == 0) and (not os.path.exists('01/CONTCAR') or os.path.getsize('01/CONTCAR') == 0)):
            raise Exception('empty CONTCAR')
        incar = Incar.from_file('INCAR')
        print(incar)
        kpoints = Kpoints.from_file('KPOINTS')
        stages = Upgrade_Run.parse_incar_update('{{ CONVERGENCE }}')
        stage_number = incar['STAGE_NUMBER']
        if i == 0:
            settings = Upgrade_Run.parse_stage_update(stages[incar['STAGE_NUMBER']], incar)
        else:
            stage_number += 1
            if stage_number >= len(stages):
                break
            settings = Upgrade_Run.parse_stage_update(stages[stage_number], incar)
            settings += continuation
        if stage_number == len(stages) - 1:
            final = True
        else:
            final = False
        if ('LNONCOLLINEAR' in incar or 'LSORBIT' in incar):
            #vasp = vasp_ncl
            vasp ='/home/rtrottie/programs/vasp/5.4.4.2019/bin/vasp_ncl'
        elif ('AUTO_GAMMA' in incar and incar['AUTO_GAMMA']):
            vasp = os.environ['VASP_GAMMA']
        else:
            vasp = vasp_kpts
        yield job(['{{ mpi }}',{% if mpi != "srun" %} '-np', '{{ tasks }}',{% endif %} vasp], '{{ logname }}', auto_npar=False, settings_override=settings, final=final)


c = Custodian(handlers, get_runs(), max_errors=1000, skip_over_errors=True)
c.run()
{% endblock python %}
