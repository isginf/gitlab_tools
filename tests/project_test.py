import unittest
import time
import sys
sys.path.append('..')

import gitlab_lib
import gitlab_config

#gitlab_lib.core.DEBUG = True

class ProjectTest(unittest.TestCase):
    def _create_test_user(self):
        return gitlab_lib.create_user("projtestuser", "Test User", "projtest@localhost", {"reset_password": "no",
                                                                                  "password": "woohoo123",
                                                                                  "projects_limit": 0,
                                                                                  "admin": "no",
                                                                                  "can_create_group": "no",
                                                                                  "skip_confirmation": "yes"})

    def _create_test_project(self):
        user = self._create_test_user()
        return gitlab_lib.create_project("testproject", {'owner': user['id']})

    def _delete_test_prokect(self):
        gitlab_lib.delete_project("testproject")
        gitlab_lib.delete_user("projtestuser")

    def test_get_project(self):
        self._create_test_project()
        project = gitlab_lib.get_project("testproject")
        self.assertTrue(type(project) == dict, "Got " + str(project))
        self.assertTrue(project.get('name') == "testproject", "Got " + str(project))
        # self.assertTrue(project['owner']['username'] == "projtestuser", "Got " + str(project))
        self._delete_test_project()

    def test_create_project(self):
        project = gitlab_lib.create_project("testproject")
        self.assertTrue(type(project) == dict, "Got " + str(project))
        self.assertTrue(project.get('name') == "testproject", "Got " + str(project))
        gitlab_lib.delete_project("testproject")

    def test_delete_project(self):
        self._create_test_project()
        gitlab_lib.delete_project("testproject")
        time.sleep(1)

        project = gitlab_lib.get_user("testproject")
        self.assertFalse(project)
