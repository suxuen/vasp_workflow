#!/usr/bin/env python
import yaml
import argparse
import os
import sys
from yaml_generation.writeyaml import WriteYaml
from pathlib import Path

def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--outfile_name', help='Output .yml file path', type=str, required=True)
    parser.add_argument(
        '-c', '--copyfile_name', help='Copied .yml file path', type=str, default=None)
    parser.add_argument(
        '-e', '--edit_fields', help='Fields to edit', nargs='+', type=str,
        choices=['MPIDs', 'PATHs', 'Calculation_Type', 'Relaxation_Set',
                 'Magnetization_Scheme', 'INCAR_Tags', 'KPOINTs',
                 'Max_Submissions'], default=None)
    args = parser.parse_args()

    return args

def reorder_args(args):
    input_args_ind = []
    ordering = ['MPIDs', 'PATHs', 'Calculation_Type', 'Relaxation_Set',
                'Magnetization_Scheme', 'INCAR_Tags', 'KPOINTs',
                'Max_Submissions']
    try:
        for arg in args.edit_fields:
            if arg in ordering:
                input_args_ind.append(ordering.index(arg))
            else:
                print('Bad argument passed; fatal error')
                sys.exit(1)
        sorted_inputs_ind = sorted(input_args_ind)
        sorted_inputs = [ordering[val] for val in sorted_inputs_ind]
        return sorted_inputs
    except TypeError:
        return None

def yml_inputs(args, args_fields):
    # add in something to organize the fields read-in in the manner that you want them read-in
    WY = WriteYaml(args.copyfile_name)

    if args_fields is None:
        pass

    else:
        for field in args_fields:

            if field == 'MPIDs':
                WY.validate_mpids()

            if field == 'PATHs':
                WY.validate_paths()

            if field == 'Calculation_Type':
                WY.validate_calculation_type()

            if field == 'Relaxation_Set':
                WY.validate_general_string('Relaxation_Set', WY.allowed_relaxation_sets,
                                           'Base Relax Set from Materials Project (')

            if field == 'Magnetization_Scheme':
                WY.validate_magnetization()

            if field == 'INCAR_Tags':
                WY.add_or_edit_convergence_step()

            if field == 'KPOINTs':
                WY.add_or_edit_kpoints()

            if field == 'Max_Submissions':
                WY.validate_general_positive_integer('Max_Submissions',
                                                     'Number of Workflow Submissions')

    return WY.new_dictionary

def write_yaml(write_dict, path):
    # writes a dictionary to the path as a .yml file
    abs_path = os.path.abspath(path)
    parent = Path(abs_path).parent
    if '.yml' in path and os.path.exists(parent):
        print('Writing new .yml to path %s' % abs_path)
        with open(abs_path, "w") as outfile:
            yaml.safe_dump(write_dict, outfile, default_flow_style=False)
    else:
        new_path = input('Provide write path that exists; file should have .yml file extension'/n)
        write_yaml(write_dict, new_path)

def main():
    args = argument_parser()
    ordered_args = reorder_args(args)
    yml_dict = yml_inputs(args, ordered_args)
    write_yaml(yml_dict, args.outfile_name)

if __name__ == "__main__":
    main()
