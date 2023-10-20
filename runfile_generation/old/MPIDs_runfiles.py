#!/usr/bin/env python

import yaml
import argparse
import os
import sys
import random
import numpy as np
from pymatgen.ext.matproj import MPRester
from pymatgen.analysis.magnetism.analyzer import \
    CollinearMagneticStructureAnalyzer
from pymatgen.io.vasp.sets import batch_write_input
from configuration.config import MP_api_key


def load_yaml(path):
    # loads a .yml file from the specified path
    with open(path, 'r') as loadfile:
        read_yaml = yaml.safe_load(loadfile)
    return read_yaml


def get_MP_structures(mpid_list, mp_key=MP_api_key):
    # gets structure objects from mpids list
    structures = []
    with MPRester(mp_key) as m:
        for mpid in mpid_list:
            try:
                structure = m.get_structures(mpid, final=True)[0]
                structures.append(structure)
            except BaseException:
                print('%s is not a valid mp-id' % mpid)
    return structures


def random_antiferromagnetic(ferro_magmom, used_enumerations,
                             num_rand, num_tries):
    # checks if all unique iterations complete OR too many tries achieved
    if num_rand == 0 or num_tries == 0:
        return used_enumerations
    # checks if proposed enumeration is the ferromagnetic enumeration
    dont_use = False
    antiferro_mag_scheme = random.choices([-1, 1], k=len(ferro_magmom))
    antiferro_mag = np.multiply(antiferro_mag_scheme, ferro_magmom)
    if np.array_equal(antiferro_mag, np.array(ferro_magmom)):
        dont_use = True
    # checks if proposed scheme is an already existing antiferromagnetic scheme
    for used_enumeration in used_enumerations:
        if np.array_equal(antiferro_mag, used_enumeration):
            dont_use = True
    # if dont_use = True: tries again with num_tries - 1
    if dont_use is True:
        return random_antiferromagnetic(ferro_magmom, used_enumerations,
                                        num_rand, num_tries - 1)
    # else: appends to used_enumerations: tries again with num_rand - 1
    else:
        used_enumerations.append(antiferro_mag)
        return random_antiferromagnetic(ferro_magmom, used_enumerations,
                                        num_rand - 1, num_tries)


def get_magnetic_structures(structures, magnetic_scheme, num_rand=10,
                            num_tries=100):
    # assigns magnetism to structures. returns the magnetic get_structures
    # num_rand and num_tries only used for random antiferromagnetic assignment
    checked_mag_structures = [[] for i in range(len(structures))]
    for structure_idx in range(len(structures)):
        col_obj = CollinearMagneticStructureAnalyzer(
            structures[structure_idx], overwrite_magmom_mode="replace_all")
        ferro_structure = col_obj.get_ferromagnetic_structure()
        if magnetic_scheme == 'ferromagnetic':
            checked_mag_structures[structure_idx].append(ferro_structure)
        elif magnetic_scheme == 'preserve':
            checked_mag_structures[structure_idx].append(
                structures[structure_idx])
        elif magnetic_scheme == 'antiferromagnetic':
            if set(ferro_structure.site_properties["magmom"]) == set([0]):
                print("%s is not magnetic; ferromagnetic structure to be run"
                      % str(ferro_structure.formula))
                checked_mag_structures[structure_idx].append(ferro_structure)
            else:
                random_enumerations = random_antiferromagnetic(
                    ferro_structure.site_properties["magmom"], [], num_rand,
                    num_tries)
                for enumeration in random_enumerations:
                    antiferro_structure = ferro_structure.copy()
                    for magmom_idx in range(
                            len(antiferro_structure.site_properties[
                                "magmom"])):
                        antiferro_structure.replace(
                            magmom_idx, antiferro_structure.species[
                                magmom_idx],
                            properties={'magmom': enumeration[magmom_idx] + 0})
                    checked_mag_structures[structure_idx].append(
                        antiferro_structure)
        else:
            print('%s not supported at this time; try ferromagnetic, ' +
                  'preserve, or antiferromagnetic' % magnetic_scheme)
            sys.exit(1)
    return checked_mag_structures

def write_vasp_input_files(structures, formulas, mpids, convergence_scheme,
                           user_inputs, write_path):
    package = 'pymatgen.io.vasp.sets'
    relax_set = getattr(__import__(package, fromlist=[convergence_scheme]),
                        convergence_scheme)

    for structure_list_idx in range(len(structures)):
        name = str(formulas[structure_list_idx]).replace(' ', '')
        mpid = str(mpids[structure_list_idx]).replace('-', '_')
        structure_write_dir = os.path.join(write_path, (name + '_' + mpid))
        batch_write_input(structures[structure_list_idx],
                          vasp_input_set=relax_set,
                          output_dir=structure_write_dir,
                          make_dir_if_not_present=True,
                          user_incar_settings=user_inputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-r',
        '--read_yaml_path',
        help='Path to the .yml file to read',
        type=str,
        required=True)
    parser.add_argument(
        '-o',
        '--output_directory_path',
        help='Path to where the output directory WILL BE created. ' +
        'User-specify /Path/To/Folder, full path will add the ' +
        '"Relaxation_Scheme" value from .yml file',
        type=str,
        required=True)

    args = parser.parse_args()

    if os.path.exists(args.read_yaml_path):
        read_dict = load_yaml(args.read_yaml_path)
        structures = get_MP_structures(read_dict['MPIDs'])
        mag_structures = get_magnetic_structures(structures,
                                                 read_dict['Magnetism'])
        output_write_path = os.path.join(args.output_directory_path,
                                         read_dict['Relaxation_Scheme'])
        write_vasp_files(mag_structures, read_dict['Formulas'],
                         read_dict['MPIDs'], read_dict['Convergence_Scheme'],
                         read_dict['Additional_INCAR_tags'],
                         output_write_path)
    else:
        print('%s is not a valid path to a .yml file' % args.read_yaml_path)
        sys.exit(1)


if __name__ == "__main__":
    main()
