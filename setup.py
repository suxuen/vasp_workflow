#!/usr/bin/env python

import os
from pathlib import Path

setup_path = os.path.abspath(__file__)
vasp_workflow_path = os.path.dirname(setup_path)
workflow_scripts_path = os.path.join(vasp_workflow_path, 'workflow_scripts')
vasp_run_path = os.path.join(vasp_workflow_path, 'vasp_run')

def write_api_key():
    pass

def make_scripts_in_path_executable(path):
    make_executable = []
    for file_or_dir in os.listdir(path):
        if file_or_dir == '__init__.py':
            continue
        else:
            abs_path = os.path.join(path, file_or_dir)
            if Path(abs_path).suffix == '.py' and os.path.exists(abs_path):
                make_executable.append(abs_path)
            else:
                continue

    for script in make_executable:
        os.system('chmod 755 ' + script)
        print('Made %s executable' % Path(script).name)

if __name__ == '__main__':
    make_scripts_in_path_executable(workflow_scripts_path)
    make_scripts_in_path_executable(vasp_run_path)
