import unittest
import time
import sys
sys.path.append('..')

import gitlab_lib
import gitlab_config

class JobTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_get_jobs(self):
        jobs = gitlab_lib.get_jobs("test")
        self.assertTrue(len(list(jobs)) > 0, "Got jobs")
