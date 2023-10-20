#!/usr/bin/env python

import yaml
import os
import sys
import random
import numpy as np
import copy
from pymatgen.ext.matproj import MPRester
from configuration.mp_api import MP_api_key
from pymatgen.io.vasp import Poscar
from pymatgen.analysis.magnetism.analyzer import \
    CollinearMagneticStructureAnalyzer
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.core.periodic_table import Element
from pymatgen.core.structure import Structure
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.io.vasp.outputs import Outcar
from pymatgen.io.vasp.inputs import Kpoints
from pymatgen.io.vasp.sets import get_structure_from_prev_run
from pymatgen.io.vasp.sets import batch_write_input
from yaml.scanner import ScannerError
import tempfile
import shutil


class LoadYaml:

    def __init__(self, load_path):
        if os.path.exists(load_path):
            try:
                with open(load_path, 'r') as loadfile:
                    loaded_dictionary = yaml.safe_load(loadfile)
                    self.loaded_dictionary = loaded_dictionary
            except ScannerError:
                print('Invalid .yml; try again or use default dictionary')
                sys.exit(1)
        else:
            print('Path to %s does not exist' % load_path)
            sys.exit(1)

        try:
            self.mpids = self.loaded_dictionary['MPIDs']
        except KeyError:
            print('MPIDs not in %s; invalid input file' % load_path)
            sys.exit(1)
        try:
            self.paths = self.loaded_dictionary['PATHs']
        except KeyError:
            print('PATHs not in %s; invalid input file' % load_path)
            sys.exit(1)
        try:
            self.calculation_type = self.loaded_dictionary['Calculation_Type']
        except KeyError:
            print('Calculation_Type not in %s; invalid input file' % load_path)
            sys.exit(1)
        try:
            self.relaxation_set = self.loaded_dictionary['Relaxation_Set']
        except KeyError:
            print('Relaxation_Set not in %s; invalid input file' % load_path)
            sys.exit(1)
        try:
            self.magnetization_scheme = self.loaded_dictionary['Magnetization_Scheme']
        except KeyError:
            print(
                'Magnetization_Scheme not in %s; invalid input file' %
                load_path)
            sys.exit(1)
        try:
            self.incar_tags = self.loaded_dictionary['INCAR_Tags']
        except KeyError:
            print('INCAR_Tags not in %s; invalid input file' % load_path)
            sys.exit(1)
        try:
            self.kpoints = self.loaded_dictionary['KPOINTs']
        except KeyError:
            print('KPOINTs not in %s; invalid input file' % load_path)
            sys.exit(1)
        try:
            self.max_submissions = self.loaded_dictionary['Max_Submissions']
        except KeyError:
            print('Max_Submissions not in %s; invalid input file' % load_path)
            sys.exit(1)


class PmgStructureObjects:
    def __init__(self, mpids, paths, rescale):
        self.mpids = mpids
        self.paths = paths
        self.rescale = rescale
        self.structures_dict = {}
        self.structure_number = 1

        self.mpid_structures()
        self.path_structures()

    def structure_rescaler(self, structure):
        if len(structure.species) <= 2:
            structure.make_supercell([4, 4, 4])
        elif len(structure.species) <= 4:
            structure.make_supercell([3, 3, 3])
        elif len(structure.species) <= 7:
            structure.make_supercell([3, 3, 2])
        elif len(structure.species) <= 10:
            structure.make_supercell([3, 2, 2])
        elif len(structure.species) <= 16:
            structure.make_supercell([2, 2, 2])
        elif len(structure.species) <= 32:
            structure.make_supercell([2, 2, 1])
        elif len(structure.species) <= 64:
            structure.make_supercell([2, 1, 1])
        else:
            pass
        return structure

    def mpid_structures(self):
        for mpid in self.mpids:
            with MPRester(MP_api_key) as m:
                try:
                    structure = m.get_structures(mpid, final=True)[0]
                    if self.rescale == True:
                        structure = self.structure_rescaler(structure)
                    structure_key = str(structure.formula) + ' ' + str(self.structure_number)
                    self.structures_dict[structure_key] = structure
                    self.structure_number += 1
                except BaseException:
                    print('%s is not a valid mp-id' % mpid)
                    continue

    def path_structures(self):
        for path in self.paths:
            parent_dir = os.path.dirname(os.path.abspath(path))
            vasprun_path = os.path.join(parent_dir, 'vasprun.xml')
            outcar_path = os.path.join(parent_dir, 'OUTCAR')
            if os.path.exists(vasprun_path) == True and os.path.exists(outcar_path) == True:
                try:
                    V = Vasprun(vasprun_path)
                    O = Outcar(outcar_path)
                    structure = get_structure_from_prev_run(V, O)
                    if self.rescale == True:
                        structure = self.structure_rescaler(structure)
                    structure_key = str(structure.formula) + ' ' + str(self.structure_number)
                    self.structures_dict[structure_key] = structure
                    self.structure_number += 1
                except UnicodeDecodeError:
                    print('Either %s or %s not readable' % (vasprun_path, outcar_path))
                    continue
                except OSError:
                    print('Either %s or %s not readable' % (vasprun_path, outcar_path))
                    continue
            else:
                try:
                    poscar = Poscar.from_file(path)
                    structure = poscar.structure
                    if self.rescale == True:
                        structure = self.structure_rescaler(structure)
                    structure_key = str(structure.formula) + ' ' + str(self.structure_number)
                    self.structures_dict[structure_key] = structure
                    self.structure_number += 1
                except FileNotFoundError:
                    print('%s path does not exist' % path)
                    continue
                except UnicodeDecodeError:
                    print('%s likely not a valid CONTCAR or POSCAR' % path)
                    continue
                except OSError:
                    print('%s likely not a valid CONTCAR or POSCAR' % path)
                    continue

class Magnetism:
    def __init__(self, structures_dict, magnetization_dict):
        self.structures_dict = structures_dict
        self.magnetization_dict = magnetization_dict
        self.magnetized_structures_dict = {}
        try:
            self.num_tries = self.magnetization_dict['Max_antiferro']*5 # Avoid recursion errors
        except:
            self.num_tries = 0
        self.structure_number = 1
        self.unique_magnetizations = {}

        self.get_magnetic_structures()

    def random_antiferromagnetic(self, ferro_magmom, used_enumerations, num_afm, num_tries):
        # checks if all unique iterations complete OR too many tries achieved
        if num_afm == 0 or num_tries == 0:
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
            return self.random_antiferromagnetic(ferro_magmom, used_enumerations,
                                            num_afm, num_tries - 1)
        # else: appends to used_enumerations: tries again with num_rand - 1
        else:
            used_enumerations.append(antiferro_mag)
            return self.random_antiferromagnetic(ferro_magmom, used_enumerations,
                                            num_afm, num_tries - 1)

    def afm_structures(self, structure_key, ferro_structure):
        # sets magnetism on a structures key and assigns to self.magnetized_structures_dict
        if set(ferro_structure.site_properties["magmom"]) == set([0]):
            print("%s is not magnetic; ferromagnetic structure to be run"
                    % str(ferro_structure.formula))
            self.magnetized_structures_dict[structure_key]['FM'] = ferro_structure
            self.unique_magnetizations[structure_key]['FM'] = ferro_structure.site_properties["magmom"]
        else:
            random_enumerations = self.random_antiferromagnetic(
                ferro_structure.site_properties["magmom"], [],
                self.magnetization_dict['Max_antiferro'], self.num_tries)
            afm_enum_number = 1
            written = 0
            for enumeration in random_enumerations:
                antiferro_structure = ferro_structure.copy()
                for magmom_idx in range(len(antiferro_structure.site_properties["magmom"])):
                    antiferro_structure.replace(magmom_idx, antiferro_structure.species[magmom_idx], properties={'magmom': enumeration[magmom_idx] + 0})
                # Check to make sure the structure isn't equal to any existing structures
                exists = False
                csm = CollinearMagneticStructureAnalyzer(antiferro_structure)
                for existing_key in list(self.magnetized_structures_dict[structure_key]):
                     matches = csm.matches_ordering(self.magnetized_structures_dict[structure_key][existing_key])
                     if matches == True:
                         exists = True
                         break
                     else:
                         pass
                # Write to the magnetism dictionary if the structure does not exist
                if exists == False:
                    afm_key = 'AFM' + str(afm_enum_number)
                    self.magnetized_structures_dict[structure_key][afm_key] = antiferro_structure
                    self.unique_magnetizations[structure_key][afm_key] = antiferro_structure.site_properties["magmom"]
                    afm_enum_number += 1
                    written += 1
                else:
                    pass

                # Break condition if Max_antiferro is reached
                if written == self.magnetization_dict['Max_antiferro']:
                    break

    def get_magnetic_structures(self):
        # assigns magnetism to structures. returns the magnetic get_structures
        # num_rand and num_tries only used for random antiferromagnetic assignment
        for structure in self.structures_dict.values():
            collinear_object = CollinearMagneticStructureAnalyzer(
                structure, make_primitive=False, overwrite_magmom_mode="replace_all")
            ferro_structure = collinear_object.get_ferromagnetic_structure(make_primitive=False)
            structure_key = str(structure.formula) + ' ' + str(self.structure_number)
            self.unique_magnetizations[structure_key] = {}
            self.magnetized_structures_dict[structure_key] = {}

            if self.magnetization_dict['Scheme'] == 'preserve':
                self.magnetized_structures_dict[structure_key]['preserve'] = structure
                try:
                    self.unique_magnetizations[structure_key]['preserve'] = structure.site_properties["magmom"]
                except KeyError:
                    self.unique_magnetizations[structure_key]['preserve'] = ferro_structure.site_properties["magmom"]

            elif self.magnetization_dict['Scheme'] == 'FM':
                self.magnetized_structures_dict[structure_key]['FM'] = ferro_structure
                self.unique_magnetizations[structure_key]['FM'] = ferro_structure.site_properties["magmom"]

            elif self.magnetization_dict['Scheme'] == 'AFM':
                self.afm_structures(structure_key, ferro_structure)

            elif self.magnetization_dict['Scheme'] == 'FM+AFM':
                self.magnetized_structures_dict[structure_key]['FM'] = ferro_structure
                self.unique_magnetizations[structure_key]['FM'] = ferro_structure.site_properties["magmom"]
                self.afm_structures(structure_key, ferro_structure)

            else:
                print('Magnetization Scheme %s not recognized; fatal error' % self.magnetization_dict['Scheme'])
                sys.exit(1)

            self.structure_number += 1


class CalculationType:
    def __init__(self, magnetic_structures_dict, calculation_dict):
        self.magnetic_structures_dict = magnetic_structures_dict
        self.calculation_dict = calculation_dict
        self.calculation_structures_dict = copy.deepcopy(self.magnetic_structures_dict)
        self.unique_defect_sites = None

        self.alter_structures()

    def get_unique_sites(self, structure):
        SGA = SpacegroupAnalyzer(structure)
        symm_structure = SGA.get_symmetrized_structure()
        equivalent_sites = symm_structure.as_dict()['equivalent_positions']
        unique_site_indices, site_counts = np.unique(equivalent_sites, return_counts=True)
        periodic_site_list = []
        for ind in unique_site_indices:
            periodic_site_list.append(symm_structure.sites[ind])

        unique_site_dict = {}
        for i in range(len(periodic_site_list)):
            unique_site_dict[periodic_site_list[i]] = {}
            unique_site_dict[periodic_site_list[i]]['Index'] = unique_site_indices[i]
            unique_site_dict[periodic_site_list[i]]['Equivalent Sites'] = site_counts[i]
        return unique_site_dict

    def alter_structures(self):
        if self.calculation_dict['Type'] == 'bulk':
            for structure in self.calculation_structures_dict.keys():
                for magnetism in self.calculation_structures_dict[structure].keys():
                    base_structure = self.calculation_structures_dict[structure][magnetism]
                    bulk_dict = {}
                    bulk_key = str(base_structure.formula)
                    bulk_dict[bulk_key] = base_structure
                    self.calculation_structures_dict[structure][magnetism] = bulk_dict

        elif self.calculation_dict['Type'] == 'defect':
            self.unique_defect_sites = {}
            defect_element = self.calculation_dict['Defect']
            for structure in self.calculation_structures_dict.keys():
                for magnetism in self.calculation_structures_dict[structure].keys():
                    base_structure = self.calculation_structures_dict[structure][magnetism]
                    unique_site_dict = self.get_unique_sites(base_structure)

                    defect_dict = {}
                    # defect_key = str(defect_element) + ' Defect '
                    defect_number = 1
                    unique_defects_dict = {}
                    for periodic_site in unique_site_dict.keys():
                        #defect_structure = copy.deepcopy(rescaled_structure)
                        defect_structure = copy.deepcopy(base_structure) # Fix this so re-scaling can be performed here
                        if Element(periodic_site.as_dict()['species'][0]['element']) == Element(defect_element):
                            unique_defects_dict[periodic_site] = unique_site_dict[periodic_site]
                            defect_structure.remove_sites([unique_site_dict[periodic_site]['Index']])
                            defect_key = str(defect_structure.formula)
                            defect_dict[defect_key + ' ' + str(defect_number)] = defect_structure
                            unique_defects_dict[periodic_site]['Run Directory Name'] = str(defect_key + ' ' + str(defect_number)).replace(' ', '_')
                            defect_number += 1
                        else:
                            continue
                    self.calculation_structures_dict[structure][magnetism] = defect_dict
                    if unique_defects_dict != {}:
                        self.unique_defect_sites[structure] = unique_defects_dict

        else:
            print('Calculation Type %s not recognized; fatal error' % self.calculation_dict['Type'])
            sys.exit(1)


class WriteVaspFiles:
    def __init__(self, calculation_structures_dict, calculation_dict,
                 relaxation_set, incar_tags, kpoints):
        self.calculation_structures_dict = calculation_structures_dict
        self.calculation_dict = calculation_dict
        self.relaxation_set = relaxation_set
        self.incar_tags = incar_tags
        self.kpoints = kpoints

        self.write_vasp_inputs()

    def check_directory_existence(self, directory):
        try:
            os.mkdir(directory)
        except FileExistsError:
            pass

    def get_relax_set(self):
        package = 'pymatgen.io.vasp.sets'
        relax_set = getattr(__import__(package, fromlist=[self.relaxation_set]),
                            self.relaxation_set)
        return relax_set

    def get_0_step(self):
        # gets lowest number step
        steps = list(self.kpoints.keys())
        if len(steps) == 0:
            print('No "0 Step" KPOINTs params supplied; using %s default' % self.relaxation_set)
            return None
        else:
            if "0 Step" in steps:
                return "0 Step"
            else:
                print('No "0 Step" KPOINTs params supplied; using %s default' % self.relaxation_set)
                return None

    def get_kpoints_object(self, step, structure):
        try:
            kpoints_tags = self.kpoints[step]
        except KeyError:
            return None

        if kpoints_tags['Type'] == 'automatic_density':
            K = Kpoints.automatic_density(structure, kpoints_tags['Grid Density'],
                                        kpoints_tags['Force Gamma'])
        elif kpoints_tags['Type'] == 'automatic_density_by_vol':
            K = Kpoints.automatic_density_by_vol(structure, kpoints_tags['Grid Density per A^(-3) of Reciprocal Cell'],
                                        kpoints_tags['Force Gamma'])
        elif kpoints_tags['Type'] == 'automatic_gamma_density':
            K = Kpoints.automatic_gamma_density(structure, kpoints_tags['Grid Density'])
        elif kpoints_tags['Type'] == 'gamma_automatic':
            K = Kpoints.gamma_automatic(kpoints_tags["KPTS"], kpoints_tags["Shift"])
        elif kpoints_tags['Type'] == 'monkhorst_automatic':
            K = Kpoints.monkhorst_automatic(kpoints_tags["KPTS"], kpoints_tags["Shift"])
        else:
            print('Invalid kpoints generation type %s; fatal error' % kpoints_tags['Type'])
            sys.exit(1)
        return K

    def format_convergence_file(self, structure):
        all_steps = []
        for step in list(self.incar_tags.keys()):
            step_array = []
            step_array.append('\n' + step + '\n')
            for tag in list(self.incar_tags[step].keys()):
                step_array.append(tag + ' = ' + str(self.incar_tags[step][tag]))
            if step in list(self.kpoints.keys()):
                K = self.get_kpoints_object(step, structure)
                kpoints_string = " "
                step_array.append('\nKPOINTS ' + kpoints_string.join(map(str, K.kpts[0])))
            all_steps += step_array
        return all_steps

    def rewrite_magmom(self, incar_path, magmoms):
        string = 'MAGMOM = '
        for m in magmoms:
            if m == 0:
                string += '3*0 '
            else:
                string += '0 0 %s ' % str(m) # Currently only works for SAXIS = 0 0 1, which is the default
        return string + '\n'

    def replace_string(self, file_name, pattern, string):
        t = tempfile.NamedTemporaryFile(mode="r+")
        i = open(file_name, 'r')
        for line in i:
            t.write(string if pattern in line else line)
        i.close()
        t.seek(0)
        o = open(file_name, 'w')
        for line in t:
            o.write(line)
        t.close()

    def insert_string(self, file_name, string, index=3):
        f = open(file_name, "r")
        contents = f.readlines()
        f.close()

        contents.insert(index, string)

        f = open(file_name, "w")
        contents = "".join(contents)
        f.write(contents)
        f.close()

    def remove_line(self, file_name, pattern):
        t = tempfile.NamedTemporaryFile(mode="r+")
        i = open(file_name, 'r')
        for line in i:
            if not pattern in line:
                t.write(line)
        i.close()
        t.seek(0)
        o = open(file_name, 'w')
        for line in t:
            o.write(line)
        t.close()

    def write_vasp_inputs(self):
        if self.calculation_dict['Type'] == 'bulk':
            calc = 'bulk'
        elif self.calculation_dict['Type'] == 'defect':
            calc = str(self.calculation_dict['Defect']) + ' defect'

        relax_set = self.get_relax_set()
        first_step = self.get_0_step()

        top_level_dirname = self.calculation_dict['Type']
        self.check_directory_existence(top_level_dirname)
        for structure in self.calculation_structures_dict.keys():
            structure_dirname = structure.replace(' ', '_')
            structure_dir_path = os.path.join(top_level_dirname, structure_dirname)
            for magnetism in self.calculation_structures_dict[structure].keys():
                magnetism_dirname = magnetism.replace(' ', '_')
                magnetism_dir_path = os.path.join(structure_dir_path, magnetism_dirname)
                if not bool(self.calculation_structures_dict[structure][magnetism]) == True:
                    # empty dictionary check; sometimes occurs with defect calcs
                    print('%s not compatible with %s calculation' % (structure, calc))
                    continue
                else:
                    for calculation_type in self.calculation_structures_dict[structure][magnetism].keys():
                        calculation_type_dirname = calculation_type.replace(' ', '_')
                        calculation_type_dir_path = os.path.join(magnetism_dir_path, calculation_type_dirname)
                        write_structure = self.calculation_structures_dict[structure][magnetism][calculation_type]
                        if type(write_structure) == Structure:
                            kpoints_object = self.get_kpoints_object(first_step, write_structure)
                            self.check_directory_existence(structure_dir_path)
                            self.check_directory_existence(magnetism_dir_path)
                            self.check_directory_existence(calculation_type_dir_path)
                            try:
                                user_incar_settings = self.incar_tags["0 Step"]
                            except:
                                user_incar_settings = None
                            v = relax_set(write_structure,
                                          user_incar_settings=user_incar_settings,
                                          user_kpoints_settings=kpoints_object)
                            v.write_input(calculation_type_dir_path)

                            with open(os.path.join(calculation_type_dir_path,'CONVERGENCE'),'w') as f:
                                for line in self.format_convergence_file(write_structure):
                                    f.write("%s\n" % line)
                                f.close()

                            if 'LSORBIT' in user_incar_settings or 'LNONCOLLINEAR' in user_incar_settings:
                                if user_incar_settings['LSORBIT'] == True or user_incar_settings['LNONCOLLINEAR'] == True:
                                    incar_file_path = os.path.join(calculation_type_dir_path, 'INCAR')
                                    convergence_file_path = os.path.join(calculation_type_dir_path, 'CONVERGENCE')
                                    rewrite_line = self.rewrite_magmom(incar_file_path, write_structure.site_properties['magmom'])
                                    self.insert_string(convergence_file_path, rewrite_line)
                                    self.remove_line(incar_file_path, 'MAGMOM')
                                    #self.replace_string(incar_file_path, 'MAGMOM', rewrite_line + '\n')

                            if 'LUSE_VDW' in user_incar_settings:
                                if user_incar_settings['LUSE_VDW'] == True: # Van der Waals kernel needed
                                    file_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
                                    shutil.copyfile(os.path.join(file_path, 'extra_vasp_files/vdw_kernel.bindat'), os.path.join(calculation_type_dir_path, 'vdw_kernel.bindat'))

                        else:
                            print('Not valid structure type')
                            continue
