#
# Central lib for Gitlab Tools - Backup code
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
# Loading modules
#

import os
import json
import tarfile
from .core import *
from .api import *
from .users import get_user
from .projects import get_projects


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
    result = True
    filename = "%s%s.tgz" % (prefix, os.path.basename(src_dir))

    try:
        tar = tarfile.open(os.path.join(dest_dir, filename), "w:gz")
        tar.add(src_dir, arcname=".")
        tar.close()
    except (FileExistsError):
        os.unlink(filename)
        archivate(src_dir, filename)
    except (tarfile.TarError, OSError) as e:
        result = False
        log("Error creating tar archive %s from directory %s: %s" % (filename, directory, str(e)))

    return result


def archive_directory(project, component, directory, backup_dir):
    """
    Archivate directory to backup_dir
    """
    result = False

    if os.path.exists(directory):
        log("Backing up %s from project %s [ID %s]" % (component, project['name'], project['id']))

        if component == "upload":
            result = archivate(directory, backup_dir, "upload_")
        else:
            result = archivate(directory, backup_dir)
    else:
        log("No %s found for project %s [ID %s]" % (component, project['name'], project['id']))
        result = True

    return result


def backup_local_data(repository_dir, upload_dir, backup_dir, project):
    """
    Backup repository upload and wiki data locally for the given project
    """
    success = False
    src_dirs = { "repository": os.path.join(repository_dir, project['namespace']['name'], project['name'] + ".git"),
                 "wiki": os.path.join(repository_dir, project['namespace']['name'], project['name'] + ".wiki.git"),
                 "upload": os.path.join(upload_dir, project['namespace']['name'], project['name']) }

    for (component, directory) in src_dirs.items():
        try_again = 3

        while try_again:
            success = archive_directory(project, component, directory, backup_dir)

            if success:
                try_again = False
            else:
                try_again = try_again - 1

                if not try_again:
                    log("Failed to backup %s %s" % (project['name'], component))

    return success


def backup_snippets(api_url, project, backup_dir):
    """
    Backup snippets and their contents
    snippet contents must be backuped by additional api call
    """
    log(u"Backing up snippets from project %s [ID %s]" % (project['name'], project['id']))

    snippets = fetch(api_url % (API_URL, project['id']))

    dump(backup_dir, "snippets.json", snippets)

    for snippet in snippets:
        dump(backup_dir,
             "snippet_%d_content.dump" % (snippet['id'],),
             rest_api_call(GET_SNIPPET_CONTENT % (API_URL, project['id'], snippet['id']), method="GET").text)

        notes = fetch(NOTES_FOR_SNIPPET % (API_URL, project['id'], snippet['id']))

        if notes:
            dump(backup_dir, "snippet_%d_notes.dump" % (snippet['id'],), notes)


def backup_issues(api_url, project, token, backup_dir):
    """
    Backup all issues of a project
    issue notes must be backuped by additional api call
    """
    log(u"Backing up issues from project %s [ID %s]" % (project['name'], project['id']))

    issues = fetch(api_url % (API_URL, project['id']))

    dump(backup_dir, "issues.json", issues)

    for issue in issues:
        notes = fetch(NOTES_FOR_ISSUE % (API_URL, project['id'], issue['id']))

        if notes:
            dump(backup_dir, "issue_%d_notes.dump" % (issue['id'],), notes)


def backup_user_metadata(user, output_basedir):
    """
    Backup all metadata including email addresses and SSH keys of a single user
    """

    if not type(user) == dict:
        user = get_user(username)

    if user:
        backup_dir = os.path.join(output_basedir, "user_%s_%s" % (user['id'], user['username']))
        if not os.path.exists(output_basedir): os.mkdir(output_basedir)
        if not os.path.exists(backup_dir): os.mkdir(backup_dir)

        log(u"Backing up metadata of user %s [ID %s]" % (user["username"], user["id"]))
        dump(backup_dir, "user.json", user)
        dump(backup_dir, "projects.json", list(get_projects(user["username"])))
        dump(backup_dir, "ssh.json", fetch(USER_SSHKEYS % (API_URL, user["id"])))
        dump(backup_dir, "email.json", fetch(USER_EMAILS % (API_URL, user["id"])))


def backup_project(project, repository_dir, upload_dir, backup_dir):
    """
    Backup a single project
    """
    dump(backup_dir, "project.json", project)

    # shall we backup local data like repository and wiki?
    if repository_dir:
        success = backup_local_data(repository_dir, upload_dir, backup_dir, project)

        if not success and not project.get("retried"):
            project["retried"] = True
            queue.put(project)

    # backup metadata of each component
    for (component, api_url) in PROJECT_COMPONENTS.items():
        # issues
        if component == "issues" and \
           project.get(component + "_enabled") == True:
            backup_issues(api_url, project, TOKEN, backup_dir)

        # snippets
        elif component == "snippets" and \
           project.get(component + "_enabled") == True:
            backup_snippets(api_url, project, backup_dir)

        # milestones are enabled if either issues or merge_requests are enabled
        # labels cannot be disabled therefore no labels_enabled field exists
        # otherwise check if current component is enabled in project
        elif component == "milestones" and \
             (project.get("issues_enabled") == True or project.get("merge_requests_enabled") == True):
            log(u"Backing up %s from project %s [ID %s]" % (component, project['name'], project['id']))
            dump(backup_dir,
                 component + ".json",
                 fetch(api_url % (API_URL, project['id'])))

        elif project.get(component + "_enabled") and project.get(component + "_enabled") == True:
            dump(backup_dir,
                 component + ".json",
                 fetch(api_url % (API_URL, project['id'])))

        elif component != "milestones" and \
             component != "snippets" and \
             component != "issues" and \
             project.get(component + "_enabled", "not_disabled") == "not_disabled":
            dump(backup_dir,
                 component + ".json",
                 fetch(api_url % (API_URL, project['id'])))


def backup(repository_dir, upload_dir, output_basedir, queue):
    """
    Backup everything for the given project
    For every project create a dictionary with id_name as pattern
    Dump project metadata and each component as separate JSON files
    """
    while not queue.empty():
        project = queue.get()
        backup_dir = os.path.join(output_basedir, "%s_%s_%s" % (project['id'], project['namespace']['name'], project['name']))
        if not os.path.exists(backup_dir): os.mkdir(backup_dir)
        backup_project(project, repository_dir, upload_dir, backup_dir)
