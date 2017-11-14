#!/usr/bin/python3

#
# Restore Gitlab issues of a single project using the REST API
#
# Copyright 2017 ETH Zurich, ISGINF, Bastian Ballmann
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
# LOADING MODULES
#

import os
import sys
import argparse
from signal import signal, SIGINT
from multiprocessing import Queue, Manager
import gitlab_config
import gitlab_lib


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--backup_dir", help="Project directory in backup dir")
parser.add_argument("-c", "--component", help="Component to restore", choices=gitlab_lib.PROJECT_COMPONENTS.keys())
parser.add_argument("-d", "--debug", help="Activate debug mode", action="store_true")
parser.add_argument("-n", "--number", help="Number of processes", default=3)
parser.add_argument("-p", "--project", help="Project name or id in Gitlab")
parser.add_argument("-q", "--quiet", help="No messages execpt errors", action="store_true")
parser.add_argument("-r", "--repository", help="Repository directory")
parser.add_argument("-s", "--server", help="Gitlab server name", default=gitlab_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=gitlab_config.TOKEN)
parser.add_argument("-w", "--wait", help="Timeout for processes in seconds", default=3)
args = parser.parse_args()

if not args.server or not args.token or not args.project or not args.backup_dir:
    print("You must at least specify --server, --token, --project and --backup_dir")
    sys.exit(1)

work_queue = Queue()
result_dict = Manager().dict()
processes = []
gitlab_lib.core.DEBUG = args.debug
gitlab_lib.TOKEN = args.token
gitlab_lib.SERVER = args.server


#
# SUBROUTINES
#

def fill_restore_queue(project, component):
    """
    Fill queue with restore data
    project is project metadata dictionary
    component is the name of the component like the keys in PROJECT_COMPONENTS
    """
    restore_file = os.path.join(args.backup_dir, component + ".json")
    restored = False

    if os.path.isfile(restore_file):
        backup = gitlab_lib.parse_json(restore_file)

        if backup:
            for entry in backup:
                entry['component'] = component
                entry['project_id'] = project['id']
                work_queue.put(entry)
                restored = True

    if not restored:
        gitlab_lib.log("Nothing to do for " + component)

#
# SIGNAL HANDLERS
#

def clean_shutdown(signal, frame):
    for process in processes:
        process.terminate()

signal(SIGINT, clean_shutdown)


#
# MAIN PART
#

# Check backup exists and looks reasonable
if not os.path.exists(args.backup_dir):
    gitlab_lib.log(args.backup_dir + " is not a readable.")
    sys.exit(1)

if not os.path.exists(os.path.join(args.backup_dir, "project.json")):
    gitlab_lib.log(args.backup_dir + " does not look like a projects backup dir. No project.json file found!")
    sys.exit(1)

# Lookup metadata of destination project
project_data = gitlab_lib.get_project_metadata(args.project)

if not project_data or len(project_data) == 0:
    gitlab_lib.log("Cannot find project " + args.project)
    sys.exit(1)

if len(project_data) > 1:
    gitlab_lib.log("Found more then one project for " + args.project)
    sys.exit(1)

# Restore only one component?
if args.component:
    fill_restore_queue(project_data[0], args.component)

# Restore all (but issues at the end, they link to lots of other components)
else:
    for component in filter(lambda x: x != "issues", gitlab_lib.PROJECT_COMPONENTS.keys()):
        fill_restore_queue(project_data[0], component)

    fill_restore_queue(project_data[0], "issues")

# spawn some processes to do the actual restore
nr_of_processes = args.number

if work_queue.qsize() < args.number:
    nr_of_processes = work_queue.qsize()

for process in range(nr_of_processes):
    processes.append( gitlab_lib.create_process(gitlab_lib.restore, (args.backup_dir, project_data[0], work_queue, result_dict)) )

sys.exit(0)
