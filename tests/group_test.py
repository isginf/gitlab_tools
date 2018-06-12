import unittest
import time
import sys
sys.path.append('..')

import gitlab_lib
import gitlab_config

class GroupTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        gitlab_lib.delete_group("testgroup")

    def _create_test_group(self):
        return gitlab_lib.create_group("testgroup")

    def test_get_group(self):
        self._create_test_group()
        group = gitlab_lib.get_group("testgroup")
        self.assertTrue(type(group) == dict)
        self.assertTrue(group.get('name') == "testgroup")

    def test_create_group(self):
        group = self._create_test_group()
        self.assertTrue(type(group) == dict)
        self.assertTrue(group.get('name') == "testgroup")

    def test_delete_group(self):
        self._create_test_group()
        gitlab_lib.delete_group("testgroup")
        time.sleep(1)

        group = gitlab_lib.get_group("testgroup")
        self.assertFalse(group)
