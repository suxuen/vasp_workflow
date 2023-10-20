#!/usr/bin/env python

import unittest
import sys
import os
import io
import subprocess
import yaml
import numpy as np
import MPIDs_runfiles


class TestMPIDs_runfiles(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # create example_yaml.yml if it dne; read in dict from this
        workflow_path = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        yaml_gen_path = os.path.join(workflow_path, 'yaml_generation')
        MPIDs_yaml_path = os.path.join(yaml_gen_path, 'MPIDs_yaml.py')
        example_yaml_path = os.path.join(yaml_gen_path, 'example_yaml.yml')
        # yaml file creation from paths specified above
        args = ['python', MPIDs_yaml_path, '-a', 'mp-500', '-o',
                example_yaml_path]
        subprocess.call(args, shell=False)
        with open(example_yaml_path, 'r') as testfile:
            self.test_yaml = yaml.safe_load(testfile)
            self.test_yaml_path = example_yaml_path

    def test_load_yaml(self):
        # assert that the yaml file created is properly loaded
        self.assertEqual(
            self.test_yaml,
            MPIDs_runfiles.load_yaml(self.test_yaml_path))

    def test_get_MP_structures(self):
        # make sure that structure objects are correctly loaded
        structures = MPIDs_runfiles.get_MP_structures(self.test_yaml['MPIDs'])
        self.assertEqual(structures[0].formula, self.test_yaml['Formulas'][0])

    def test_random_antiferromagnetic(self):
        # test that random antiferromagnetic works for GdAlO3
        structures = MPIDs_runfiles.get_MP_structures(['mp-5223'])
        ferro_structure = MPIDs_runfiles.get_magnetic_structures(
            structures, 'ferromagnetic')[0][0]
        num_rand = 10
        num_tries = 100
        antiferro_magmoms = MPIDs_runfiles.random_antiferromagnetic(
            ferro_structure.site_properties["magmom"], [], num_rand, num_tries)
        self.assertEqual(len(antiferro_magmoms), num_rand)
        self.assertEqual(len(np.unique(antiferro_magmoms, axis=1)), num_rand)

    def test_get_magnetic_structures(self):
        # test the assignment of the magnetism scheme for GdAlO3 (mp-5223)
        structures = MPIDs_runfiles.get_MP_structures(['mp-5223'])
        ferro_structures = MPIDs_runfiles.get_magnetic_structures(
            structures, 'ferromagnetic')
        preserved_structures = MPIDs_runfiles.get_magnetic_structures(
            structures, 'preserve')
        antiferro_structures = MPIDs_runfiles.get_magnetic_structures(
            structures, 'antiferromagnetic')
        ferro = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 7.94, 7.94, 7.94, 7.94]
        preserved = [6.932, 6.933, 6.933, 6.932, 0.0, 0.0, 0.0, 0.0,
                     0.003, 0.002, 0.003, 0.003, 0.003, 0.002, 0.003,
                     0.003, 0.002, 0.003, 0.003, 0.002]
        self.assertEqual(
            ferro, ferro_structures[0][0].site_properties["magmom"])
        self.assertEqual(
            preserved,
            preserved_structures[0][0].site_properties["magmom"])
        for i in range(len(antiferro_structures[0])):
            self.assertNotEqual(
                ferro, antiferro_structures[0][i].site_properties["magmom"])

        # test that TaSe2 (mp-500) doesn't attempt antiferromagnetic ordering
        old_stdout = sys.stdout
        result = io.StringIO()
        sys.stdout = result
        nonmag_structures = MPIDs_runfiles.get_MP_structures(['mp-500'])
        nonmag_structure = MPIDs_runfiles.get_magnetic_structures(
            nonmag_structures, 'antiferromagnetic')
        sys.stdout = old_stdout
        result_string = result.getvalue()
        self.assertEqual(
            'Ta2 Se4 is not magnetic; ferromagnetic structure to be run',
            result_string.strip('\n'))
        self.assertEqual(nonmag_structure[0][0].site_properties["magmom"],
                         [0, 0, 0, 0, 0, 0])

    def test_write_vasp_input_files(self):
        # Test that structures folder is correctly written
        structures = MPIDs_runfiles.get_MP_structures(['mp-500', 'mp-5223'])
        ferro_structures = MPIDs_runfiles.get_magnetic_structures(
            structures, 'antiferromagnetic')
        output_write_directory = os.path.dirname(os.path.abspath(__file__))
        output_write_path = os.path.join(output_write_directory,
                                         self.test_yaml['Relaxation_Scheme'])
        MPIDs_runfiles.write_vasp_input_files(
            ferro_structures, ['Ta Se2', 'Gd4 Al4 012'],
            ['mp-500', 'mp-5223'], self.test_yaml['Convergence_Scheme'],
            self.test_yaml['Additional_INCAR_tags'], output_write_path)
        bulk_dir = os.path.join(os.getcwd(), 'bulk')
        # 'bulk' directory exists
        self.assertEqual(os.path.exists(bulk_dir), True)
        args = ['rm', '-r', 'bulk']
        subprocess.call(args, shell=False)

    @classmethod
    def tearDownClass(self):
        # Removes the temporary example_yaml.yml file used for testing
        args = ['rm', self.test_yaml_path]
        subprocess.call(args, shell=False)


if __name__ == "__main__":
    unittest.main()
