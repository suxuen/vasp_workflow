#!/usr/bin/env python

import yaml
import os
import sys
from pymatgen.ext.matproj import MPRester
import json
import copy
from configuration import mp_api
from configuration.mp_api import MP_api_key
from distutils.util import strtobool
from yaml.scanner import ScannerError
from pymatgen.core.periodic_table import Element
from pymatgen.io.vasp.inputs import Poscar
from pathlib import Path


class WriteYaml():

    def __init__(self, copy_path):
        self.parent_folder = os.path.dirname(os.path.abspath(mp_api.__file__))
        # expects the write_parameters and incar_parameters files to be
        # in the configuration directory
        with open(os.path.join(self.parent_folder, "yml_write_parameters.json")) as write_params:
            self.write_params = json.loads(write_params.read())

        self.exit_commands = self.write_params["Exit Commands"]
        self.allowed_relaxation_sets = self.write_params["MP Relaxation Sets"]
        self.allowed_magnetism = self.write_params["Magnetic Schemes"]
        self.allowed_vtst_tools_tags = self.write_params["VTST Tags"]
        self.allowed_calculation_types = self.write_params["Calculation Types"]
        self.allowed_incar_steps = self.write_params["Calculation Steps"]
        self.allowed_kpoints_types = self.write_params["KPOINTS Generation"]

        with open(os.path.join(self.parent_folder, "incar_parameters.json")) as incar_params:
            self.incar_params = json.loads(incar_params.read())

        if copy_path is not None:
            if os.path.exists(copy_path):
                try:
                    with open(copy_path, 'r') as copyfile:
                        copied_dictionary = yaml.safe_load(copyfile)
                        self.default_dictionary = copied_dictionary
                except ScannerError:
                    print('Invalid .yml; try again or use default dictionary')
                    sys.exit(1)
            else:
                print('Path to %s does not exist' % copy_path)
                sys.exit(1)
        else:
            self.default_dictionary = self.write_params["Default Inputs"]

        self.new_dictionary = copy.deepcopy(self.default_dictionary)

    def is_float(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    def is_bool(self, string):
        try:
            bool(strtobool(string))
            return True
        except:
            return False

    def is_pos_or_zero_float(self, string):
        try:
            float(string)
            if float(string) >= 0:
                return True
            else:
                return False
        except ValueError:
            return False

    def is_pos_int(self, string):
        try:
            int(string)
            if int(string) > 0:
                return True
            else:
                return False
        except ValueError:
            return False

    def string_to_int_tuple(self, string):
        try:
            tuple(map(int, string.split(' ')))
            return True
        except ValueError:
            return False

    def is_mpid(self, mpid):
        with MPRester(MP_api_key) as m:
            try:
                structure = m.get_structures(mpid, final=True)[0]
                return True
            except BaseException:
                print('%s is not a valid mp-id' % mpid)
                return False

    def is_vasp_readable_structure(self, path):
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

    def validate_general_positive_integer(self, tag, prompt_statement):
        print('%s; existing value is %s' % (tag, self.new_dictionary[tag]))
        integer_value = input(
            prompt_statement +
            ': should be a positive integer\n')
        if self.is_pos_int(integer_value) is True:
            self.new_dictionary[tag] = int(integer_value)
            print('New value "%s" updated for %s' % (integer_value, tag))
        elif integer_value.lower() in self.exit_commands:
            print(
                'Exiting: existing value "%s" will be used' %
                self.new_dictionary[tag])
            return
        else:
            print(
                '"%s" not an accepted value; try again or exit' %
                integer_value)
            self.validate_general_positive_integer(tag, prompt_statement)

    def validate_general_string(self, tag, accepted_values, prompt_statement):
        print('%s; existing value is %s' % (tag, self.new_dictionary[tag]))
        string_value = input(prompt_statement + str(accepted_values) + ')\n')
        if string_value in accepted_values:
            self.new_dictionary[tag] = str(string_value)
            print('New value "%s" updated for %s' % (string_value, tag))
        elif string_value.lower() in self.exit_commands:
            print(
                'Exiting: existing value "%s" will be used' %
                self.new_dictionary[tag])
            return
        else:
            print('"%s" not an accepted value; try again' % string_value)
            self.validate_general_string(
                tag, accepted_values, prompt_statement)

    def check_valid_LDAU_value(self, tag):
        try:
            print('Add %s tag; existing tags are %s' %
                  (tag, self.new_dictionary['INCAR_Tags'][tag]))
            tag_dict = self.new_dictionary['INCAR_Tags'][tag].copy()
        except KeyError:
            print('Add %s tag; no existing tags' % tag)
            tag_dict = {}
        element = input('%s element; i.e. Gd, Ce, La, etc.\n' % tag)
        try:
            Element(element)
            value = input('%s value for element %s\n' % (tag, element))
            if self.is_pos_or_zero_float(value):
                tag_dict[element] = float(value)
                return tag_dict
            else:
                print('%s not a positive or zero value' % value)
                self.check_valid_LDAU_value(tag)
        except ValueError:
            print('%s not a valid element' % element)
            self.check_valid_LDAU_value(tag)

    def check_valid_incar_value(self, dictionary, tag, value):
        if type(dictionary[tag]).__name__ == "str":
            if dictionary[tag] == 'int':
                try:
                    return int(value)
                except ValueError:
                    print(
                        '%s requires integer; %s not an integer\n' %
                        (tag, value))
                    return 'bad_value'
            elif dictionary[tag] == 'float':
                try:
                    return float(value)
                except ValueError:
                    print('%s requires float; %s not a float\n' % (tag, value))
                    return 'bad_value'
            elif dictionary[tag] == 'bool':
                try:
                    return bool(strtobool(value))
                except ValueError:
                    print('%s requires bool; %s not a bool\n' % (tag, value))
                    return 'bad_value'
                except AttributeError:
                    print('%s requires bool; %s not a bool\n' % (tag, value))
                    return 'bad_value'
            elif dictionary[tag] == 'list':
                print(
                    '\n*** WARNING *** List required for this tag; inputs '
                    'may not be appropriate. Consult VASP documentation\n')
                print(
                    'List inputs. Ex. [1, 2, 3] should be input as 1 2 3\n')
                value_list = list(value.split(' '))
                try:
                    value_list = list(map(float, value_list))
                except ValueError:
                    pass
                try:
                    return list(value_list)
                except BaseException:
                    print('%s requires list; %s not a list\n' % (tag, value))
                    return 'bad_value'
        elif type(dictionary[tag]).__name__ == "list":
            try:
                value = int(value)
            except ValueError:
                pass
            if value not in dictionary[tag]:
                return 'bad_value'
            else:
                return value
        else:
            print('%s input type not supported' % tag)

    def add_or_edit_convergence_step(self):
        print(
            'Add/edit INCAR convergence step; existing steps are \n\n %s\n' %
            self.new_dictionary['INCAR_Tags'])
        print(
            'Can also exit with one of the allowed exit commands %s' %
            self.exit_commands)
        add_or_edit = input('Add or edit steps?\n')
        if add_or_edit in self.exit_commands:
            print(
                'Exiting: existing INCAR values \n\n %s will be used \n' %
                self.new_dictionary['INCAR_Tags'])
            return
        elif add_or_edit.lower() == 'edit':
            step_to_edit = input(
                'Step to edit; existing steps are %s\n' % str(
                    list(
                        self.new_dictionary['INCAR_Tags'].keys())))
            if step_to_edit in list(self.new_dictionary['INCAR_Tags'].keys()):
                action = input(
                    'Change %s; allowed inputs are "rename", '
                    '"modify" and "delete"\n' % step_to_edit)
                if action.lower() == 'rename':
                    rename_step = input('Rename %s to what?\n' % step_to_edit)
                    if rename_step in self.allowed_incar_steps and rename_step not in list(self.new_dictionary['INCAR_Tags'].keys()):
                        self.new_dictionary['INCAR_Tags'][rename_step] = self.new_dictionary['INCAR_Tags'].pop(
                            step_to_edit)
                    else:
                        if rename_step not in self.allowed_incar_steps:
                            print(
                                '%s not an allowed step name. Allowed names are %s' %
                                (rename_step, self.allowed_incar_steps))
                        if rename_step in list(
                                self.new_dictionary['INCAR_Tags'].keys()):
                            print(
                                '%s already a step name; choose a different step name for this step first' %
                                rename_step)
                elif action.lower() == 'modify':
                    self.validate_incar_tags(step_to_edit)
                elif action.lower() == 'delete':
                    self.new_dictionary['INCAR_Tags'].pop(step_to_edit)
                    try:
                        self.new_dictionary['KPOINTs'].pop(step_to_edit)
                    except KeyError:
                        pass
                else:
                    print('%s not a valid action; try again\n')
                self.add_or_edit_convergence_step()
            else:
                print('%s not a current step; try again\n' % step_to_edit)
                self.add_or_edit_convergence_step()
        elif add_or_edit.lower() == 'add':
            step_to_add = input('Step to add; existing steps are %s\n' % str(
                list(self.new_dictionary['INCAR_Tags'].keys())))
            if step_to_add in self.allowed_incar_steps and step_to_add not in list(
                    self.new_dictionary['INCAR_Tags'].keys()):
                self.new_dictionary['INCAR_Tags'][step_to_add] = {}
                self.validate_incar_tags(step_to_add)
            else:
                if step_to_add not in self.allowed_incar_steps:
                    print(
                        '%s not an allowed step name. Allowed names are %s\n' %
                        (step_to_add, self.allowed_incar_steps))
                if step_to_add in list(
                        self.new_dictionary['INCAR_Tags'].keys()):
                    print(
                        '%s already a step name; to change it, choose to edit a convergence step\n' %
                        step_to_add)
            self.add_or_edit_convergence_step()
        else:
            print('Not a valid option; try again\n')
            self.add_or_edit_convergence_step()

    def validate_incar_tags(self, step):
        print('Add/remove INCAR_Tags for %s; existing tags are %s' %
              (step, self.new_dictionary['INCAR_Tags'][step]))
        add_or_remove = input('Add or remove tags?\n')
        if add_or_remove.lower() == 'add':
            tag = input('Name of tag to add\n')
            if tag == 'AUTO_TIME' or tag == 'AUTO_CORES' or tag == 'AUTO_NODES':
                # inputs specifically made for vasp.py; not VASP defaults
                value = input('Value of tag to add\n')
                if self.is_pos_int(value):
                    self.new_dictionary['INCAR_Tags'][step][tag] = int(value)
                else:
                    print('%s not a valid input for %s' % (tag, value))
            elif tag in ['LDAUU', 'LDAUJ', 'LDAUL']:
                print('\nWARNING: ADDING USER TAGS WILL OVERWRITE EXISTING %s %s TAGS' % (self.new_dictionary['Relaxation_Set'], tag))
                print('Check https://pymatgen.org/pymatgen.io.vasp.sets.html for pre-existing tags\n')
                value_dict = self.check_valid_LDAU_value(tag)
                self.new_dictionary['INCAR_Tags'][step][tag] = value_dict
            elif tag in self.allowed_vtst_tools_tags.keys():
                value = input('Value of tag to add\n')
                check_value = self.check_valid_incar_value(
                    self.allowed_vtst_tools_tags, tag, value)
                if check_value != 'bad_value':
                    self.new_dictionary['INCAR_Tags'][step][tag] = check_value
                else:
                    print('Invalid value %s for INCAR tag %s' % (value, tag))
            elif tag not in self.incar_params.keys():
                print('%s not a valid INCAR tag; try again' % tag)
            else:
                value = input('Value of tag to add\n')
                check_value = self.check_valid_incar_value(
                    self.incar_params, tag, value)
                if check_value != 'bad_value':
                    self.new_dictionary['INCAR_Tags'][step][tag] = check_value
                else:
                    print('Invalid value %s for INCAR tag %s' % (value, tag))
            self.validate_incar_tags(step)
        elif add_or_remove.lower() == 'remove':
            tag = input('Name of tag to remove\n')
            self.new_dictionary['INCAR_Tags'][step].pop(tag, None)
            self.validate_incar_tags(step)
        elif add_or_remove.lower() in self.exit_commands:
            print('Exiting: existing tags will be used')
            return
        else:
            print('Not a valid option; try again')
            self.validate_incar_tags(step)

    def validate_kpoints(self, step):
        if step == "0 Step":
            allowed_types = self.allowed_kpoints_types
        else:
            # for multi-step convergence where only gamma is used
            allowed_types = ['automatic_gamma_density', 'gamma_automatic']
        type = input('KPOINTs generation type; allowed values for %s are %s\n' % (step, allowed_types))
        if type in allowed_types:
            new_kpoints_dict = {}
            if type == 'automatic_density':
                new_kpoints_dict["Type"] = 'automatic_density'
                grid_density = input("Grid Density\n")
                if self.is_pos_int(grid_density) == True:
                    new_kpoints_dict["Grid Density"] = int(grid_density)
                else:
                    print('Invalid grid density')
                    self.validate_kpoints(step)
                force_gamma = input("Force gamma centered mesh? True/False\n")
                if self.is_bool(force_gamma) == True:
                    new_kpoints_dict["Force Gamma"] = bool(strtobool(force_gamma))
                else:
                    print('Invalid answer to force gamma')
                    self.validate_kpoints(step)
                return new_kpoints_dict
            elif type == 'automatic_density_by_vol':
                new_kpoints_dict["Type"] = 'automatic_density_by_vol'
                grid_density = input("Grid Density by Volume (per inverse Angstrom^3)\n")
                if self.is_pos_int(grid_density) == True:
                    new_kpoints_dict["Grid Density per A^(-3) of Reciprocal Cell"] = int(grid_density)
                else:
                    print('Invalid grid density')
                    self.validate_kpoints(step)
                force_gamma = input("Force gamma centered mesh? True/False\n")
                if self.is_bool(force_gamma) == True:
                    new_kpoints_dict["Force Gamma"] = bool(strtobool(force_gamma))
                else:
                    print('Invalid answer to force gamma')
                    self.validate_kpoints(step)
                return new_kpoints_dict
            elif type == 'automatic_gamma_density':
                new_kpoints_dict["Type"] = 'automatic_gamma_density'
                grid_density = input("Grid Density\n")
                if self.is_pos_int(grid_density) == True:
                    new_kpoints_dict["Grid Density"] = int(grid_density)
                else:
                    print('Invalid grid density')
                    self.validate_kpoints(step)
                return new_kpoints_dict
            elif type == 'gamma_automatic':
                new_kpoints_dict["Type"] = 'gamma_automatic'
                kpts = input('KPTs subdivisions along N1, N2 and N3 reciprocal lattice vectors (as len3 tuple of integers)\n')
                if self.string_to_int_tuple(kpts) == True:
                    kpts_tuple = tuple(map(int, kpts.split(' ')))
                    if len(kpts_tuple) == 3:
                         new_kpoints_dict["KPTS"] = kpts_tuple
                    else:
                        print('Invalid KPTS specified; should be len3 tuple of integers')
                        self.validate_kpoints(step)
                else:
                    print('Input %s cannot be mapped to tuple of integers' % kpts)
                    self.validate_kpoints(step)
                shift = input('Grid shift applied to KPTs (as len3 tuple)\n')
                if self.string_to_int_tuple(shift) == True:
                    shift_tuple = tuple(map(int, shift.split(' ')))
                    if len(shift_tuple) == 3:
                         new_kpoints_dict["Shift"] = shift_tuple
                    else:
                        print('Invalid Shift specified; should be len3 tuple of integers')
                        self.validate_kpoints(step)
                else:
                    print('Input %s cannot be mapped to tuple of integers' % shift)
                    self.validate_kpts(step)
                return new_kpoints_dict
            elif type == 'monkhorst_automatic':
                new_kpoints_dict["Type"] = 'monkhorst_automatic'
                kpts = input('KPTs subdivisions along N1, N2 and N3 reciprocal lattice vectors (as len3 tuple of integers)\n')
                if self.string_to_int_tuple(kpts) == True:
                    kpts_tuple = tuple(map(int, kpts.split(' ')))
                    if len(kpts_tuple) == 3:
                         new_kpoints_dict["KPTS"] = kpts_tuple
                    else:
                        print('Invalid KPTS specified; should be len3 tuple of integers')
                        self.validate_kpoints(step)
                else:
                    print('Input %s cannot be mapped to tuple of integers' % kpts)
                    self.validate_kpts(step)
                shift = input('Grid shift applied to KPTs (as len3 tuple)\n')
                if self.string_to_int_tuple(shift) == True:
                    shift_tuple = tuple(map(int, shift.split(' ')))
                    if len(shift_tuple) == 3:
                         new_kpoints_dict["Shift"] = shift_tuple
                    else:
                        print('Invalid Shift specified; should be len3 tuple of integers')
                        self.validate_kpoints(step)
                else:
                    print('Input %s cannot be mapped to tuple of integers' % shift)
                    self.validate_kpts(step)
                return new_kpoints_dict
            else:
                print('%s not supported at this time; please insert another' % type)
                self.validate_kpoints(step)
        else:
            print('%s not supported at this time; please insert another' % type)
            self.validate_kpoints(step)

    def add_or_edit_kpoints(self):
        print('Add/edit/remove KPOINTs steps; existing tags are \n\n %s \n' % self.new_dictionary['KPOINTs'])
        print('Can [add, edit, remove] steps existing in INCAR_Tags %s' % list(self.new_dictionary['INCAR_Tags'].keys()))
        add_or_edit = input('Add, edit or remove KPOINTs steps?\n')
        if add_or_edit.lower() == 'remove':
            step_to_remove = input('Step to remove\n')
            if step_to_remove in self.new_dictionary['KPOINTs']:
                self.new_dictionary['KPOINTs'].pop(step_to_remove)
            else:
                print('%s not an existing KPOINTs tag')
            self.add_or_edit_kpoints()
        if add_or_edit.lower() == 'add':
            step_to_add = input('Step to add\n')
            if step_to_add in self.new_dictionary['INCAR_Tags']:
                self.new_dictionary['KPOINTs'][step_to_add] = self.validate_kpoints(step_to_add)
            else:
                print('%s not an existing INCAR_Tags step; try again' % step_to_add)
            self.add_or_edit_kpoints()
        elif add_or_edit.lower() == 'edit':
            step_to_edit = input('Step to edit\n')
            if step_to_edit in self.new_dictionary['KPOINTs']:
                self.new_dictionary['KPOINTs'][step_to_edit] = self.validate_kpoints(step_to_edit)
            else:
                print('Step %s does not exist in tags; try adding this step' % step_to_edit)
            self.add_or_edit_kpoints()
        elif add_or_edit.lower() in self.exit_commands:
            print('Exiting: existing tags %s will be used' % self.new_dictionary['KPOINTs'])
            return
        else:
            print('Not a valid option; try again')
            self.add_or_edit_kpoints()

    def validate_magnetization(self):
        print('Magnetization_Scheme; existing is %s' %
              self.new_dictionary['Magnetization_Scheme'])
        magnetization = input(
            'Input new scheme (%s' %
            self.allowed_magnetism + ')\n')
        if magnetization.upper() == 'FM':
            self.new_dictionary['Magnetization_Scheme']['Scheme'] = 'FM'
            try:
                del self.new_dictionary['Magnetization_Scheme']['Max_antiferro']
            except KeyError:
                pass
        elif magnetization.lower() == 'preserve':
            self.new_dictionary['Magnetization_Scheme']['Scheme'] = 'preserve'
            try:
                del self.new_dictionary['Magnetization_Scheme']['Max_antiferro']
            except KeyError:
                pass
        elif magnetization.upper() == 'AFM':
            self.new_dictionary['Magnetization_Scheme']['Scheme'] = 'AFM'
            max_number = input('Max number of antiferromagnetic structures\n')
            if self.is_pos_int(max_number):
                self.new_dictionary['Magnetization_Scheme']['Max_antiferro'] = int(
                    max_number)
            else:
                print('Not valid positive integer; try again')
                self.validate_magnetization()
        elif magnetization.upper() == 'FM+AFM':
            self.new_dictionary['Magnetization_Scheme']['Scheme'] = 'FM+AFM'
            max_number = input('Max number of antiferromagnetic structures\n')
            if self.is_pos_int(max_number):
                self.new_dictionary['Magnetization_Scheme']['Max_antiferro'] = int(
                    max_number)
            else:
                print('Not valid positive integer; try again')
                self.validate_magnetization()
        else:
            print('Not a valid option; try again')
            self.validate_magnetization()

    def validate_calculation_type(self):
        print('Calculation_Type; existing is %s' %
              self.new_dictionary['Calculation_Type'])
        calculation = input('Type (%s' % self.allowed_calculation_types + ')\n')
        if calculation.lower() == 'bulk':
            self.new_dictionary['Calculation_Type']['Type'] = 'bulk'
            try:
                del self.new_dictionary['Calculation_Type']['Defect']
            except KeyError:
                pass
            rescale = input("Rescale? [True/False]\n")
            if self.is_bool(rescale):
                self.new_dictionary['Calculation_Type']['Rescale'] = bool(strtobool(rescale))
            else:
                print('%s invalid answer for rescale' % rescale)
                self.validate_calculation_type()
        elif calculation.lower() == 'defect':
            self.new_dictionary['Calculation_Type']['Type'] = 'defect'
            rescale = input("Rescale? [True/False]\n")
            if self.is_bool(rescale):
                self.new_dictionary['Calculation_Type']['Rescale'] = bool(strtobool(rescale))
            else:
                print('%s invalid answer for rescale' % rescale)
                self.validate_calculation_type()
            element = input(
                'Defect element abbreviation; i.e. H, O, C, etc.\n')
            try:
                Element(element)
                self.new_dictionary['Calculation_Type']['Defect'] = element
            except ValueError:
                print('%s not a valid element' % element)
                self.validate_calculation_type()
        else:
            print('Not a valid option; try again')
            self.validate_calculation_type()

    def validate_mpids(self):
        # add in manual vs automatic read in from .yml file
        print(
            'Add/remove MPIDs; existing mp-ids are %s' %
            self.new_dictionary['MPIDs'])
        add_or_remove = input('Add or remove mpids?\n')
        if add_or_remove.lower() == 'add':
            mpid = input('Name of mpid to add\n')
            if self.is_mpid(mpid):
                with MPRester(MP_api_key) as m:
                    structure = m.get_structures(mpid, final=True)[0]
                    formula = structure.formula
                    self.new_dictionary['MPIDs'][mpid] = formula
            else:
                pass
            self.validate_mpids()
        elif add_or_remove.lower() == 'remove':
            mpid = input('mpid to remove\n')
            if self.is_mpid(mpid):
                try:
                    del self.new_dictionary['MPIDs'][mpid]
                except KeyError:
                    print('%s not in the list of current mpids' % mpid)
                    pass
            else:
                print('Invalid mpid; try again')
            self.validate_mpids()
        elif add_or_remove.lower() in self.exit_commands:
            print('Exiting: existing tags will be used')
            return
        else:
            print('Not a valid option; try again')
            self.validate_mpids()

    def validate_paths(self):
        # add manual vs automatic read in from .yml file
        print(
            'Add/remove structure PATHs; existing paths are %s' %
            self.new_dictionary['PATHs'])
        add_or_remove = input('Add or remove paths?\n')
        if add_or_remove.lower() == 'add':
            path = input('Name of path to add\n')
            if self.is_vasp_readable_structure(path):
                poscar = Poscar.from_file(path)
                formula = poscar.structure.formula
                self.new_dictionary['PATHs'][path] = formula
            else:
                pass
            self.validate_paths()
        elif add_or_remove.lower() == 'remove':
            path = input('path to remove\n')
            if self.is_vasp_readable_structure(path):
                try:
                    del self.new_dictionary['PATHs'][path]
                except KeyError:
                    print('%s not in the list of current paths' % path)
                    pass
            else:
                print('Invalid mpid; try again')
            self.validate_paths()
        elif add_or_remove.lower() in self.exit_commands:
            print('Exiting: existing tags will be used')
            return
        else:
            print('Not a valid option; try again')
            self.validate_paths()
