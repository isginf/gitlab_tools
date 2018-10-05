#!/usr/bin/python3

#
# Delete artifacts and traces of ci jobs older than max-days
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
sys.path.append("../")

import os
import json
import time
import argparse
from signal import signal, SIGINT
from multiprocessing import Queue
from dateutil.parser import parse
from datetime import datetime, timedelta
import gitlab_lib
import gitlab_config


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Show debug messages", action="store_true")
parser.add_argument("-n", "--number", help="Number of processes", type=int, default="4")
parser.add_argument("-D", "--dryrun", help="Don't delete anything. Just simulate", action="store_true", default=False)
parser.add_argument("-m", "--max-days", help="Delete jobs older than max days", default=90)
parser.add_argument("-P", "--project", help="Delete old jobs for projects found by given id or name")
parser.add_argument("-q", "--quiet", help="No messages execpt errors", action="store_true")
parser.add_argument("-s", "--server", help="Gitlab server name", default=gitlab_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=gitlab_config.TOKEN)
args = parser.parse_args()

if not args.server or not args.token:
    print("You must at least specify --server and --token")
    sys.exit(1)

gitlab_lib.SERVER = args.server
gitlab_lib.TOKEN = args.token
gitlab_lib.core.DEBUG = args.debug
gitlab_lib.core.QUIET = args.quiet

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
# Subroutines
#


#
# This is the main function run by the parallel processes
# It deletes jobs older than max_days
#
def delete_old_jobs(queue):
    max_date = datetime.now() - timedelta(days=int(args.max_days))

    while queue.qsize() > 0:
        project = queue.get()

        gitlab_lib.log("Getting jobs for project [%d] %s" % (project["id"], project["name_with_namespace"]))

        for job in gitlab_lib.get_jobs(project):
            job_date = parse(job["created_at"])
            max_date = max_date.replace(tzinfo=job_date.tzinfo)

            gitlab_lib.debug("Checking job %d of project [%d] %s with create date %s" % (job["id"], project["id"], project["name_with_namespace"], job["created_at"]))

            if job_date < max_date:
                gitlab_lib.log("Deleting job %d of project [%d] %s" % (job["id"], project["id"], project["name_with_namespace"]))

                if not args.dryrun:
                    gitlab_lib.delete_job(project["id"], job["id"])


#
# MAIN PART
#

if args.dryrun:
    print("Running in simulation mode\n")

gitlab_lib.debug("Setting up work queue")

if args.project:
    queue.put(gitlab_lib.get_project(args.project))
    delete_old_jobs(queue)
else:
    for project in gitlab_lib.get_projects():
        queue.put(project)

    gitlab_lib.debug("Processing work queue")

    for _ in range(args.number):
        processes.append( gitlab_lib.create_process(delete_old_jobs, (queue,)) )

    # wait for processes to finish the work
    while queue.qsize() > 0:
        time.sleep(5)

        # check if a process crashed and must be restarted
        if len(processes) < int(args.number) and queue.qsize() > len(processes):
            gitlab_lib.debug("Starting new process")
            processes.append( gitlab_lib.create_process(delete_old_jobs, (queue,)) )
