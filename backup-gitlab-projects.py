#!/usr/bin/python3

#
# Dump Gitlab metadata per project using the REST API
# Can also locally backup repositories and wikis per project
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
import json
import argparse
import tarfile
from signal import signal, SIGINT
from multiprocessing import Queue
import gitlab_lib
import gitlab_config


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Show debug messages", action="store_true")
parser.add_argument("-n", "--number", help="Number of processes", type=int, default="4")
parser.add_argument("-o", "--output", help="Output directory for backups", default=gitlab_config.BACKUP_DIR)
parser.add_argument("-q", "--quiet", help="No messages execpt errors", action="store_true")
parser.add_argument("-r", "--repository", help="Repository directory", default=gitlab_config.REPOSITORY_DIR)
parser.add_argument("-s", "--server", help="Gitlab server name", default=gitlab_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=gitlab_config.TOKEN)
parser.add_argument("-u", "--upload", help="Upload directory", default=gitlab_config.UPLOAD_DIR)
parser.add_argument("-U", "--user", help="Username to backup")
parser.add_argument("-w", "--wait", type=int, help="Timeout for processes in seconds")
args = parser.parse_args()

if not args.server or not args.token:
    print("You must at least specify --server and --token")
    sys.exit(1)

gitlab_lib.SERVER = args.server
gitlab_lib.TOKEN = args.token
gitlab_lib.core.DEBUG = args.debug
gitlab_lib.core.QUIET = args.quiet

OUTPUT_BASEDIR = args.output or "."
queue = Queue()
processes = []


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

if not os.path.exists(OUTPUT_BASEDIR):
    os.mkdir(OUTPUT_BASEDIR)

# Backup metadata of a single user
if args.user:
    gitlab_lib.backup_user_metadata(args.user, OUTPUT_BASEDIR)

# Backup all projects or only the projects of a single user
for project in gitlab_lib.get_projects(args.user, personal=True):
    queue.put(project)

# Start processes and let em backup every project
for process in range(int(args.number)):
    processes.append( gitlab_lib.create_process(gitlab_lib.backup, (args.repository, args.upload, OUTPUT_BASEDIR, queue)) )

sys.exit(0)
