#!/usr/bin/python3

#
# Update all member permission to reporter and set master
# branch of projects to protected
#
# Copyright 2018 ETH Zurich, ISGINF, Bastian Ballmann
# Email: bastian.ballmann@inf.ethz.ch
# Web: http://www.isg.inf.ethz.ch
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License.
# If not, see <http://www.gnu.org/licenses/>.

#
# Import modules
#

import sys
sys.path.append("..")

import re
import argparse
import subprocess
from multiprocessing import Queue
import gitlab_lib
import gitlab_config


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Show debug messages", action="store_true")
parser.add_argument("-G", "--group-name", help="Group name", required=True)
parser.add_argument("-q", "--quiet", help="No messages execpt errors", action="store_true")
parser.add_argument("-s", "--server", help="Gitlab server name", default=gitlab_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=gitlab_config.TOKEN)


args = parser.parse_args()

if not args.server or not args.token:
    print("Need a server and token either through parameter or gitlab_config.py!")
    sys.exit(1)

for project in gitlab_lib.get_group_projects(args.group_name):
    for user in gitlab_lib.get_project_members(project.get("id")):
        gitlab_lib.info("Member %s -> Reporter" %(user.get("name"),))
        gitlab_lib.edit_project_member(project.get("id"), user.get("id"), gitlab_lib.ACCESS_LEVEL_REPORTER)

    gitlab_lib.info("Protecting master branch of project " + project.get("name"))
    gitlab_lib.protect_branch(project.get("id"), branch="master")

gitlab_lib.info("Finished.")
