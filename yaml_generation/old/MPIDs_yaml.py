#!/usr/bin/env python

import yaml
import argparse
import os
import sys
from pymatgen.ext.matproj import MPRester
import json
from configuration.config import MP_api_key


def copy_yaml(path):
    # loads a .yml file from the specified path
    with open(path, 'r') as copyfile:
        cur_yaml = yaml.safe_load(copyfile)
    return cur_yaml


def write_yaml(write_dict, path):
    # writes a dictionary to the path as a .yml file
    with open(path, "w") as outfile:
        yaml.safe_dump(write_dict, outfile, default_flow_style=False)


def new_MPIDS(old_yaml, remove_MPIDs, add_MPIDs):
    # handles mpids added by -a tag in argparse; returns list of 'MPIDs'
    new_yaml = old_yaml.copy()
    if (remove_MPIDs[0]).lower() == 'none':
        new_yaml['MPIDs'] = new_yaml['MPIDs'] + add_MPIDs
    elif (remove_MPIDs[0]).lower() == 'all':
        new_yaml['MPIDs'] = add_MPIDs
    else:
        new_mpids = list(set(new_yaml['MPIDs'] + add_MPIDs))
        for mpid in remove_MPIDs:
            if mpid in new_mpids:
                new_mpids.remove(mpid)
        new_yaml['MPIDs'] = new_mpids
    return new_yaml['MPIDs']


def get_formulas(mpid_list, mp_key=MP_api_key):
    # checks that mpids are valid; returns lists of mpids and formulas
    good_mpids = []
    formulas = []
    with MPRester(mp_key) as m:
        for mpid in mpid_list:
            try:
                structure = m.get_structures(mpid, final=True)[0]
                formulas.append(structure.formula)
                good_mpids.append(mpid)
            except BaseException:
                print('%s is not a valid mp-id' % mpid)
    return good_mpids, formulas


def new_Dict(good_mpids, formulas, old_dict=None):
    # takes good_mpids, formulas (optionally an old dictionary) and returns an
    # updated dictionary
    if old_dict is None:
        new_dict = dict(MPIDs=good_mpids,
                        Formulas=formulas)
    else:
        new_dict = old_dict.copy()
        new_dict['MPIDs'] = good_mpids
        new_dict['Formulas'] = formulas
    return new_dict


def optional_Arguments(dictionary, incar_tags, relaxation_scheme,
                       magnetism, convergence_scheme):
    # way to add incar tags to new .yml file (specified by -o flag)
    # while including tags that already exist in a .yml file (-c flag)
    if 'Additional_INCAR_tags' in list(dictionary.keys()):
        incar_tags.update(dictionary['Additional_INCAR_tags'])
    else:
        pass

    new_dict = dict(Relaxation_Scheme=relaxation_scheme,
                    Magnetism=magnetism,
                    Additional_INCAR_tags=incar_tags,
                    Convergence_Scheme=convergence_scheme)
    dictionary.update(new_dict)
    return dictionary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        '--copyfile_name',
        help='Name of .yml file to copy; default=MP_POSCARs.yml. If ' +
        'copyfile DNE, new .yml file written with inputs provided',
        type=str,
        default='MP_POSCARs.yml')
    parser.add_argument(
        '-o',
        '--outfile_name',
        help='Name of output .yml file; default=MP_POSCARs.yml',
        type=str,
        default='MP_POSCARs.yml')
    parser.add_argument(
        '-r',
        '--remove_MPIDs',
        nargs='+',
        help='List of MPIDs to be removed from MP_POSCARs.yml for copy; ' +
             'if all, all MPIDs removed',
        type=str,
        default='none')
    parser.add_argument(
        '-a',
        '--add_MPIDs',
        nargs='+',
        help='Materials Project IDs to be added to "MP_POSCARs.yml"',
        type=str,
        required=True)
    parser.add_argument(
        '-s',
        '--relaxation_scheme',
        help='Relaxation scheme (bulk, o-vacancy, etc.) to implement',
        type=str,
        choices=['bulk'],
        default='bulk',
        required=False)
    parser.add_argument(
        '-m',
        '--magnetism',
        help='Magnetic enumeration scheme to consider: ferromagnetic sets up' +
             ' a single ferromagnetic calculation, antiferromagnetic flips ' +
             'ferromagnetic spins and preserve keeps original magnetism',
        type=str,
        choices=['ferromagnetic', 'antiferromagnetic', 'preserve'],
        default='ferromagnetic',
        required=False)
    parser.add_argument(
        '-i',
        '--incar_tags',
        help='Incar tags to add that are NOT included in the chosen ' +
        'convergence scheme; format is important. ' +
        'Default=\'{"NPAR": "1", "ISYM": "0"}\'',
        type=json.loads,
        default={'NPAR': 1, 'ISYM': 0, 'AUTO_TIME': 24},
        required=False)
    parser.add_argument(
        '-b',
        '--convergence_scheme',
        help='Convergence scheme for the workflow; available schemes in ' +
        'convergence_schemes.py',
        type=str,
        default='MPRelaxSet',
        choices=['MPRelaxSet', 'BareRelaxSet'],
        required=False)

    args = parser.parse_args()

    if args.copyfile_name is not None and os.path.exists(args.copyfile_name):
        copy_dict = copy_yaml(args.copyfile_name)
        new_mpids = new_MPIDS(copy_dict, args.remove_MPIDs, args.add_MPIDs)
        good_mpids, formulas = get_formulas(new_mpids)
        new_dict = new_Dict(good_mpids, formulas, copy_dict)
        full_dict = optional_Arguments(new_dict, args.incar_tags,
                                       args.relaxation_scheme,
                                       args.magnetism, args.convergence_scheme)
        write_yaml(full_dict, args.outfile_name)

    else:
        good_mpids, formulas = get_formulas(args.add_MPIDs)
        new_dict = new_Dict(good_mpids, formulas)
        full_dict = optional_Arguments(new_dict, args.incar_tags,
                                       args.relaxation_scheme,
                                       args.magnetism, args.convergence_scheme)
        write_yaml(full_dict, args.outfile_name)


if __name__ == "__main__":
    main()
