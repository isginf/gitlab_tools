#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Restore Gitlab issues of a single project using the REST API
#
# Copyright 2016 ETH Zurich, ISGINF, Bastian Ballmann
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
from pipes import quote
from multiprocessing import Queue
import backup_config
import gitlab_lib


#
# CONSTANTS
#

VISIBILITY_PRIVATE=0
VISIBILITY_INTERNAL=10
VISIBILITY_PUBLIC=20


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
parser.add_argument("-s", "--server", help="Gitlab server name", default=backup_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=backup_config.TOKEN)
parser.add_argument("-w", "--wait", help="Timeout for processes in seconds", default=3)
args = parser.parse_args()

if not args.server or not args.token or not args.project or not args.backup_dir:
    print("You must at least specify --server, --token, --project and --backup_dir")
    sys.exit(1)


#
# SUBROUTINES
#

def restore_entry(project, queue):
    """
    Restore a single entry of a project component
    """
    while not queue.empty():
        entry = queue.get()

        gitlab_lib.log("Restoring %s [%s]" % (entry['component'], entry.get('name') or "ID " + str(entry.get('id'))))

        # for snippets we must additionally restore the content file
        if entry['component'] == "snippets":
            restore_snippets(project, entry)
        else:
            result = gitlab_lib.rest_api_call(gitlab_lib.PROJECT_COMPONENTS[entry['component']] % (gitlab_lib.API_URL, project['id']),
                                              gitlab_lib.prepare_restore_data(project, entry))

            if entry['component'] == "issues":
                result = result.json()
                gitlab_lib.rest_api_call(gitlab_lib.ISSUE_EDIT % (gitlab_lib.API_URL, project['id'], result.get('id')),
                                         gitlab_lib.prepare_restore_data(project, update_issue_metadata(entry)),
                                         "PUT")
                restore_notes(gitlab_lib.NOTES_FOR_ISSUE % (gitlab_lib.API_URL, project['id'], str(entry.get('id'))),
                              project,
                              entry)


def restore_snippets(project, entry):
    """
    Restore a single snippet
    """
    if not entry.get('visibility_level'):
        entry['visibility_level'] = VISIBILITY_PRIVATE

    if not entry.get('file_name'):
        entry['file_name'] = quote(entry['title']).replace(" ", "_").replace("'", "") + ".txt"

        snippet_content = os.path.join(args.backup_dir, "snippet_" + str(entry.get('id')) + "_content.dump")
        entry['code'] = gitlab_lib.parse_json(snippet_content)

        if entry['code']:
            gitlab_lib.debug("RESTORE ENTRY\n\tcomponent %s\n\turl %s\n\tproject %s\n\tentry %s\n" % (entry['component'],
                                                                                                      gitlab_lib.PROJECT_COMPONENTS[entry['component']],
                                                                                                      project['id'],
                                                                                                      gitlab_lib.prepare_restore_data(project, entry)))

            gitlab_lib.rest_api_call(gitlab_lib.PROJECT_COMPONENTS["snippets"] % (gitlab_lib.API_URL, project['id']),
                                     gitlab_lib.prepare_restore_data(project, entry))

            restore_notes(gitlab_lib.NOTES_FOR_SNIPPET % (gitlab_lib.API_URL, project['id'], str(entry.get('id'))),
                          project,
                          entry)
        else:
            gitlab_lib.error("Content file of snippet " + str(entry.get('id')) + " cannot be found. Won't restore snippet!")


def restore_notes(api_url, project, entry):
    """
    Restore the notes to a component like snippets or issues
    """
    notes_file = os.path.join(args.backup_dir, entry['component'] + "_" + str(entry.get('id')) + "_notes.dump")

    if os.path.exists(notes_file):
        notes = gitlab_lib.parse_json(notes_file)

        for note in notes:
            note[entry['component'] + '_id'] = str(entry.get('id'))

            gitlab_lib.rest_api_call(api_url,
                                     gitlab_lib.prepare_restore_data(project, note))


def update_issue_metadata(entry):
    """
    Set owner and assignee, close the ticket if it was closed
    """
    if entry.get('state') == "closed":
        entry['state_event'] = "close"

    if type(entry.get("assignee")) == dict:
        entry['assignee_id'] = entry['assignee']["id"]

    if type(entry.get("milestone")) == dict:
        entry['milestone_id'] = entry['milestone']["id"]

    return entry


def fill_restore_queue(project, component):
    """
    Fill queue with restore data
    project is project metadata dictionary
    component is the name of the component like the keys in PROJECT_COMPONENTS
    """
    restore_file = os.path.join(args.backup_dir, component + ".json")
    backup = gitlab_lib.parse_json(restore_file)

    if backup:
        for entry in backup:
            entry['component'] = component
            queue.put(entry)
    else:
        gitlab_lib.log("Nothing to do for " + component)


#
# MAIN PART
#

queue = Queue()
gitlab_lib.DEBUG = args.debug
gitlab_lib.TOKEN = args.token
gitlab_lib.SERVER = args.server

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

# Restore all
else:
    for component in gitlab_lib.PROJECT_COMPONENTS.keys():
        fill_restore_queue(project_data[0], component)

# spawn some processes to do the actual restore
nr_of_processes = args.number

if queue.qsize() < args.number:
    nr_of_processes = queue.qsize()

map(lambda _: gitlab_lib.create_process(restore_entry,
                                        (project_data[0], queue)),
    range(int(nr_of_processes)))
