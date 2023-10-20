#!/usr/bin/env python

import unittest
import sys
import os
import io
import subprocess
import yaml
import MPIDs_yaml


class TestMPIDs_yaml(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # create example_yaml.yml and save dict as self.test_yaml
        args = ['python', 'MPIDs_yaml.py', '-a', 'mp-500', '-o',
                'example_yaml.yml']
        subprocess.call(args, shell=False)
        with open("example_yaml.yml", 'r') as testfile:
            self.test_yaml = yaml.safe_load(testfile)

    def test_copy_yaml(self):
        # assert that the yaml file created is properly copied
        self.assertEqual(
            self.test_yaml,
            MPIDs_yaml.copy_yaml("example_yaml.yml"))

    def test_write_yaml(self):
        # assert that a .yml file copied from example_yaml.yml is the same
        # as the original .yml file
        MPIDs_yaml.write_yaml(self.test_yaml, "example_yaml_2.yml")
        self.assertEqual(
            self.test_yaml,
            MPIDs_yaml.copy_yaml("example_yaml_2.yml"))
        args = ["rm", "example_yaml_2.yml"]
        subprocess.call(args, shell=False)

    def test_new_MPIDS(self):
        # Test the 'add', 'none' and lst() inputs for -a flag in MPIDs_yaml
        new_mpid = MPIDs_yaml.new_MPIDS(self.test_yaml, ['mp-500'], ['mp-502'])
        self.assertEqual(set(new_mpid), set(['mp-502']))
        no_mpid = MPIDs_yaml.new_MPIDS(self.test_yaml, ['mp-503'], ['mp-502'])
        self.assertEqual(set(no_mpid), set(['mp-500', 'mp-502']))
        add_mpid = MPIDs_yaml.new_MPIDS(self.test_yaml, ['none'], ['mp-502'])
        self.assertEqual(set(add_mpid), set(['mp-500', 'mp-502']))
        rm_mpid = MPIDs_yaml.new_MPIDS(self.test_yaml, ['all'], ['mp-502'])
        self.assertEqual(set(rm_mpid), set(['mp-502']))

    def test_get_formulas(self):
        # Assert that the Materials Project query function can get formulas
        # from valid mp-ids; also checks that stdout exists for mp-0 (bad mpid)
        try_mpids = ['mp-24', 'mp-0', 'mp-500', 'mp-502']
        old_stdout = sys.stdout
        result = io.StringIO()
        sys.stdout = result
        good_mpids, formulas = MPIDs_yaml.get_formulas(try_mpids)
        self.assertEqual(good_mpids, ['mp-24', 'mp-500', 'mp-502'])
        self.assertEqual(formulas, ['C8', 'Ta2 Se4', 'As8 S10'])
        sys.stdout = old_stdout
        result_string = result.getvalue()
        self.assertEqual(
            'mp-0 is not a valid mp-id',
            result_string.strip('\n'))

    def test_new_Dict(self):
        # Check that a read-in .yml file preserves all keys apart from the
        # 'MPIDs' and 'Formulas' passed to it
        good_mpids = ['mp-24', 'mp-502']
        good_formulas = ['C8', 'As8 S10']
        new_dict = MPIDs_yaml.new_Dict(good_mpids, good_formulas)
        self.assertEqual(dict(MPIDs=good_mpids, Formulas=good_formulas),
                         new_dict)
        new_old_dict = MPIDs_yaml.new_Dict(good_mpids, good_formulas,
                                           self.test_yaml)
        test_dict = self.test_yaml.copy()
        test_dict['MPIDs'] = good_mpids
        test_dict['Formulas'] = good_formulas
        self.assertEqual(new_old_dict, test_dict)

    def test_optional_Arguments(self):
        # Checks that 'Additional_INCAR_tags' passed to an existing
        # dictionary appends the new tags to the existing tags
        new_dict = MPIDs_yaml.optional_Arguments(self.test_yaml, {'LDAU': 1},
                                                 'bulk', 'ferromagnetic',
                                                 'MPRelaxSet')
        copy_dict = self.test_yaml.copy()
        copy_dict['Additional_INCAR_tags']['LDAU'] = 1
        self.assertEqual(new_dict, copy_dict)

    @classmethod
    def tearDownClass(self):
        # Removes the temporary example_yaml.yml file used for testing
        args = ['rm', 'example_yaml.yml']
        subprocess.call(args, shell=False)


if __name__ == "__main__":
    unittest.main()
