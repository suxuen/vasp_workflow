#!/usr/bin/env python

import os
import yaml
import argparse
from pathlib import Path
from pymatgen.io.vasp.inputs import Poscar

def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--outfile_name', help='Output .yml file path', type=str, required=True)
    parser.add_argument(
        '-c', '--copyfile_name', help='Copied .yml file path', type=str, required=True)
    parser.add_argument(
        '-p', '--poscars_dir', help='Path to directory with POSCAR files', type=str, required=True)
    args = parser.parse_args()

    return args

def is_vasp_readable_structure(path):
        try:
            checked_path = Path(path)
            Poscar.from_file(str(checked_path))
            return True
        except FileNotFoundError:
            print('%s path does not exist' % path)
            return False
        except UnicodeDecodeError:
            print('%s likely not a valid CONTCAR or POSCAR' % path)
            return False
        except OSError:
            print('%s likely not a valid CONTCAR or POSCAR' % path)
            return False

def get_paths_dictionary(copied_yaml, poscars_dir):
    paths = {}
    with open(copied_yaml, 'r') as yaml_file:
        copied_yaml = yaml.safe_load(yaml_file)

    for roots, dirs, files in os.walk(poscars_dir):
        for name in files:
            check_path = os.path.join(roots, name)
            if os.path.exists(check_path):
                valid_path = is_vasp_readable_structure(check_path)
                if valid_path == True:
                    poscar = Poscar.from_file(check_path)
                    formula = poscar.structure.formula
                    paths[check_path] = formula
                else:
                    pass
            else:
                pass
    copied_yaml["PATHs"] = paths
    return copied_yaml

if __name__ == '__main__':
    args = argument_parser()
    new_yaml = get_paths_dictionary(args.copyfile_name, args.poscars_dir)
    with open(args.outfile_name, 'w') as yaml_file:
        yaml.dump(new_yaml, yaml_file) 
