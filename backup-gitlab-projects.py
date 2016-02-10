#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Dump Gitlab metadata per project using the REST API
# Can also locally backup repositories and wikis per project
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
import json
import argparse
import tarfile
from multiprocessing import Queue
import gitlab_lib
import backup_config


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Show debug messages", action="store_true")
parser.add_argument("-n", "--number", help="Number of processes", type=int, default="4")
parser.add_argument("-o", "--output", help="Output directory for backups", default=backup_config.BACKUP_DIR)
parser.add_argument("-q", "--quiet", help="No messages execpt errors", action="store_true")
parser.add_argument("-r", "--repository", help="Repository directory", default=backup_config.REPOSITORY_DIR)
parser.add_argument("-s", "--server", help="Gitlab server name", default=backup_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=backup_config.TOKEN)
parser.add_argument("-u", "--upload", help="Upload directory", default=backup_config.UPLOAD_DIR)
parser.add_argument("-w", "--wait", type=int, help="Timeout for processes in seconds")
args = parser.parse_args()

if not args.server or not args.token:
    print("You must at least specify --server and --token")
    sys.exit(1)

gitlab_lib.SERVER = args.server
gitlab_lib.TOKEN = args.token
gitlab_lib.DEBUG = args.debug
gitlab_lib.QUIET = args.quiet


#
# SUBROUTINES
#

def dump(backup_dir, filename, data):
    """
    Write the given data as json to a file
    """
    out = open(os.path.join(backup_dir, filename), "w")
    json.dump(data, out)
    out.close()


def archivate(src_dir, dest_dir, prefix=""):
    """
    Zip src_dir to dest_dir
    """
    filename = "%s%s.tgz" % (prefix, os.path.basename(src_dir))

    tar = tarfile.open(os.path.join(dest_dir, filename), "w:gz")
    tar.add(src_dir, arcname=".")
    tar.close()


def archive_directory(project, component, directory, backup_dir):
    """
    Archivate directory to backup_dir
    """
    if os.path.exists(directory):
        gitlab_lib.log("Backing up %s from project %s [ID %s]" % (component, project['name'], project['id']))

        if component == "upload":
            archivate(directory, backup_dir, "upload_")
        else:
            archivate(directory, backup_dir)
    else:
        gitlab_lib.log("No %s found for project %s [ID %s]" % (component, project['name'], project['id']))


def backup_local_data(repository_dir, upload_dir, backup_dir, project):
    """
    Backup repository upload and wiki data locally for the given project
    """
    src_dirs = { "repository": os.path.join(repository_dir, project['namespace']['name'], project['name'] + ".git"),
                 "wiki": os.path.join(repository_dir, project['namespace']['name'], project['name'] + ".wiki.git"),
                 "upload": os.path.join(upload_dir, project['namespace']['name'], project['name']) }

    for (component, directory) in src_dirs.iteritems():
        archive_directory(project, component, directory, backup_dir)


def backup_snippets(api_url, project, backup_dir):
    """
    Backup snippets and their contents
    snippet contents must be backuped by additional api call
    """
    gitlab_lib.log(u"Backing up snippets from project %s [ID %s]" % (project['name'], project['id']))

    snippets = gitlab_lib.fetch(api_url % (gitlab_lib.API_URL, project['id']))

    dump(backup_dir, "snippets.json", snippets)

    for snippet in snippets:
        dump(backup_dir,
             "snippet_%d_content.dump" % (snippet['id'],),
             gitlab_lib.rest_api_call(gitlab_lib.GET_SNIPPET_CONTENT % (gitlab_lib.API_URL, project['id'], snippet['id']), method="GET").text)

        notes = gitlab_lib.fetch(gitlab_lib.NOTES_FOR_SNIPPET % (gitlab_lib.API_URL, project['id'], snippet['id']))

        if notes:
            dump(backup_dir, "snippet_%d_notes.dump" % (snippet['id'],), notes)


def backup_issues(api_url, project, token, backup_dir):
    """
    Backup all issues of a project
    issue notes must be backuped by additional api call
    """
    gitlab_lib.log(u"Backing up issues from project %s [ID %s]" % (project['name'], project['id']))

    issues = gitlab_lib.fetch(api_url % (gitlab_lib.API_URL, project['id']))

    dump(backup_dir, "issues.json", issues)

    for issue in issues:
        notes = gitlab_lib.fetch(gitlab_lib.NOTES_FOR_ISSUE % (gitlab_lib.API_URL, project['id'], issue['id']))

        if notes:
            dump(backup_dir, "issue_%d_notes.dump" % (issue['id'],), notes)


def backup(repository_dir, queue):
    """
    Backup everything for the given project
    For every project create a dictionary with id_name as pattern
    Dump project metadata and each component as separate JSON files
    """
    while not queue.empty():
        project = queue.get()
        backup_dir = os.path.join(OUTPUT_BASEDIR, "%s_%s_%s" % (project['id'], project['namespace']['name'], project['name']))
        if not os.path.exists(backup_dir): os.mkdir(backup_dir)

        dump(backup_dir, "project.json", project)

        # shall we backup local data like repository and wiki?
        if repository_dir:
            backup_local_data(repository_dir, args.upload, backup_dir, project)

        # backup metadata of each component
        for (component, api_url) in gitlab_lib.PROJECT_COMPONENTS.items():
            # issues
            if component == "issues" and \
               project.get(component + "_enabled") == True:
                backup_issues(api_url, project, args.token, backup_dir)

            # snippets
            elif component == "snippets" and \
               project.get(component + "_enabled") == True:
                backup_snippets(api_url, project, backup_dir)

            # milestones are enabled if either issues or merge_requests are enabled
            # labels cannot be disabled therefore no labels_enabled field exists
            # otherwise check if current component is enabled in project
            elif component == "milestones" and \
                 (project.get("issues_enabled") == True or project.get("merge_requests_enabled") == True) or \
                 component == "labels" or \
                 project.get(component + "_enabled") == True:
                gitlab_lib.log(u"Backing up %s from project %s [ID %s]" % (component, project['name'], project['id']))
                dump(backup_dir,
                     component + ".json",
                     gitlab_lib.fetch(api_url % (gitlab_lib.API_URL, project['id'])))

            else:
                gitlab_lib.log("Component %s disabled for project %s [ID %s]" % (component, project['name'], project['id']))


#
# MAIN PART
#

OUTPUT_BASEDIR = args.output or "."
queue = Queue()

if not os.path.exists(OUTPUT_BASEDIR):
    os.path.mkdir(OUTPUT_BASEDIR)

# Fill work queue with all projects
for project in gitlab_lib.get_projects():
    queue.put(project)

# Start processes and let em backup every project
for process in range(int(args.number)):
    gitlab_lib.create_process(backup, (args.repository, queue))
