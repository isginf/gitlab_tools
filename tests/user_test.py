import unittest
import time
import sys
sys.path.append('..')

import gitlab_lib
import gitlab_config

class UserTest(unittest.TestCase):
    def setUp(self):
        pass

    def _create_test_user(self):
        return gitlab_lib.create_user("testuser", "Test User", "test@localhost", {"reset_password": "no",
                                                                                  "password": "woohoo123",
                                                                                  "projects_limit": 0,
                                                                                  "admin": "no",
                                                                                  "can_create_group": "no",
                                                                                  "provider": "ldapmain",
                                                                                  "extern_uid": gitlab_config.LDAP_DN.replace("$USERNAME$", "testuser"),
                                                                                  "skip_confirmation": "yes"})

    def tearDown(self):
        gitlab_lib.delete_user("testuser")

    def test_get_user(self):
        user = gitlab_lib.get_user("root")
        self.assertTrue(type(user) == dict)
        self.assertTrue(user.get('username') == "root")

    def test_create_user(self):
        user = self._create_test_user()

        self.assertTrue(type(user) == dict, "Got " + str(user))
        self.assertTrue(user.get('username') == "testuser", "Got " + str(user))

        user2 = gitlab_lib.get_user("testuser")
        self.assertTrue(type(user2) == dict, "Got " + str(user2))
        self.assertTrue(user2.get('email') == "test@localhost", "Got " + str(user2))
        self.assertTrue(user2['identities'][0]['provider'] == "ldapmain", "Got " + str(user2))

    def test_update_user(self):
        user = self._create_test_user()
        gitlab_lib.update_user(user, {'projects_limit': 25})

        user2 = gitlab_lib.get_user("testuser")
        self.assertTrue(type(user2) == dict, "Got " + str(user2))
        self.assertTrue(user2.get('projects_limit') == 25, "Got " + str(user2))

    def test_delete_user(self):
        self._create_test_user()
        gitlab_lib.delete_user("testuser")
        time.sleep(1)

        user = gitlab_lib.get_user("testuser")
        self.assertFalse(user)

if __name__ == '__main__':
    unittest.main()
        
