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
import sys
import json
import shutil
import shlex
import tarfile
import traceback
import subprocess
from .core import *
from .api import *
from .users import get_user
from .projects import get_projects
from .exception import ArchiveError, CloneError


#
# SUBROUTINES
#

def dump(data, output_basedir, filename):
    """
    Write the given data as json to a file
    """
    out = open(os.path.join(output_basedir, filename), "w")
    json.dump(data, out)
    out.close()


def archivate(src_dir, dest_dir, prefix="", console=False):
    """
    Zip src_dir to dest_dir
    """
    filename = os.path.join(dest_dir, "%s%s.tgz" % (prefix, os.path.basename(src_dir)))
    error_msg = None

    try:
        if console:
            tar_cmd = "tar xvfz %s %s" % (filename, src_dir)

            with subprocess.Popen(tar_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as tar:
                tar.wait()
                tar_error = str(tar.stderr.read()).lower()

                if "fatal" in tar_error or "error" in tar_error:
                    error_msg = tar_error
        else:
            tar = tarfile.open(filename, "w:gz")
            tar.add(src_dir, arcname=".", recursive=True)
            tar.close()
    except (FileExistsError):
        os.unlink(filename)
        archivate(src_dir, dest_dir, prefix, console)
    except (FileNotFoundError) as e:
        log("Failed to tar %s with Python lib. Trying to use console tar. Error was %s" % (src_dir, str(e)))
    except (tarfile.TarError, OSError) as e:
        error_msg = str(e)

    if error_msg and not console:
        archivate(src_dir, dest_dir, prefix, console=True)
    elif error_msg:
        error(error_msg)


def archive_directory(project, component, directory, output_basedir):
    """
    Archivate directory to output_basedir
    """
    if os.path.exists(directory):
        log("Backing up %s from project %s [ID %s]" % (component, project['name'], project['id']))

        if component == "upload":
            archivate(directory, output_basedir, "upload_")
        else:
            archivate(directory, output_basedir)
    else:
        log("No %s found for project %s [ID %s]" % (component, project['name'], project['id']))


def __check_git_error(git_error):
    git_error = str(git.stderr.read()).lower()

    if "fatal" in git_error or "error" in git_error:
        if "empty repository" in git_error:
           log("Repository is empty")
        else:
            raise CloneError(repository_url, "Command %s failed: %s" %(git_cmd, git_error))


def __run_git_commands(git_commands):
    for git_cmd in git_commands:
        with subprocess.Popen(git_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as git:
            git.wait()


def __archive_repository(repository_url, clone_output_dir):
    """
    Clone a repo with all branches and resolve lfs files in all commits
    """
    git_clone_cmd = ["git", "lfs", "clone", repository_url, clone_output_dir]
    log("Cloning " + repository_url + " into " + clone_output_dir)

    with subprocess.Popen(git_clone_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as git:
        git.wait()
        git_error = str(git.stderr.read()).lower()

        # when cloning an empty repo via https git returns 403 :(
        if ("fatal" in git_error or "error" in git_error) and not "error: 403" in git_error:
            if "empty repository" in git_error:
                log("Repository is empty")
            else:
                raise CloneError(repository_url, "Failed cloning: " + str(git_error))
        elif not "error: 403" in git_error:
            os.chdir(clone_output_dir)

            # check out all branches except HEAD
            branches = list(filter(lambda x: not "HEAD" in x and not x == "master", subprocess.getoutput('git branch -r').splitlines()))

            for branch in branches:
                branch = branch.split('/')[1]
                branch = branch.replace(' ', '')
                log("Checking out branch %s of repo %s" % (branch, repository_url))

                git_commands = (["git", "checkout", branch],       # checkout branch
                                ["git", "lfs", "fetch", "--all"])  # fetch all lfs files in all commits

                __run_git_commands(git_commands)

            if len(branches) > 0:
                subprocess.getoutput("git checkout master")

            # clean up
            git_commands = ( ["untrack_lfs.sh"],                  # untrack all lfs files in all revisions
                             ["git", "gc"],                       # run garbadge collector
                             ["git", "fsck"],                     # check repo
                             ["git", "lfs", "uninstall"],         # uninstall LFS hook
                             ["git", "remote", "rm" , "origin"] ) # remove remote url

            __run_git_commands(git_commands)


def backup_repository(project, output_basedir, repository_dir=REPOSITORY_DIR, tmp_dir=TMP_DIR, resolve_lfs=False):
    """
    Backup repository either as bare mirror or as LFS resolved checkout
    """
    repo_dir = os.path.join(repository_dir, project['namespace']['name'], project['name'] + ".git")

    if not os.path.exists(repo_dir):
        log("No repository found for project %s [ID %s]" % (project['name'], project['id']))
        return None

    backup_tmp_dir = os.path.join(tmp_dir, "backup")
    namespace_tmp_dir = os.path.join(backup_tmp_dir, project['namespace']['name'])
    clone_output_dir = os.path.join(backup_tmp_dir, project['namespace']['name'], shlex.quote(project['name']) + ".git")
    repository_url = project['http_url_to_repo'].replace("https://", "https://oauth2:" + CLONE_ACCESS_TOKEN + "@")

    try:
        os.mkdir(backup_tmp_dir)
        os.mkdir(namespace_tmp_dir)
    except FileExistsError:
        pass

    if os.path.exists(clone_output_dir):
        try:
            debug("Removing " + clone_output_dir)
            shutil.rmtree(clone_output_dir)
        except (OSError, PermissionError, FileNotFoundError) as e:
            raise CloneError(repository_url, str(e))

    if resolve_lfs:
        __archive_repository(repository_url, clone_output_dir)
    else:
        git_clone_cmd = ["git", "clone", "--mirror", repository_url, clone_output_dir]
        log("Cloning " + repository_url + " into " + clone_output_dir)

        with subprocess.Popen(git_clone_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as git:
            git.wait()
            git_error = str(git.stderr.read()).lower()

            # when cloning an empty repo via https git returns 403 :(
            if ("fatal" in git_error or "error" in git_error) and not "error: 403" in git_error:
                if "empty repository" in git_error:
                    log("Repository is empty")
                else:
                    raise CloneError(repository_url, "Failed cloning: " + str(git_error))

    # zip repo
    archive_directory(project, 'repository', clone_output_dir, output_basedir)
    os.chdir("/")

    # removed temporary cloned repository
    if os.path.exists(clone_output_dir):
        try:
            debug("Removing " + clone_output_dir)
            shutil.rmtree(clone_output_dir)
        except (OSError, PermissionError, FileNotFoundError) as e:
            pass


def backup_local_data(project, output_basedir, repository_dir=REPOSITORY_DIR, upload_dir=UPLOAD_DIR):
    """
    Backup upload and wiki data locally for the given project
    """
    src_dirs = { "wiki": os.path.join(repository_dir, project['namespace']['name'], project['name'] + ".wiki.git"),
                 "upload": os.path.join(upload_dir, project['namespace']['name'], project['name']) }

    # zip all local components
    for (component, directory) in src_dirs.items():
        archive_directory(project, component, directory, output_basedir)


def backup_snippets(project, output_basedir):
    """
    Backup snippets and their contents
    snippet contents must be backuped by additional api call
    """
    log(u"Backing up snippets from project %s [ID %s]" % (project['name'], project['id']))

    snippets = fetch(PROJECT_COMPONENTS['snippets'] % (API_BASE_URL, project['id']))

    dump(snippets, output_basedir, "snippets.json")

    for snippet in snippets:
        dump(rest_api_call(GET_SNIPPET_CONTENT % (API_BASE_URL, project['id'], snippet['id']), method="GET").text,
             output_basedir,
             "snippet_%d_content.dump" % (snippet['id'],))

        notes = fetch(NOTES_FOR_SNIPPET % (API_BASE_URL, project['id'], snippet['id']))

        if notes:
            dump(notes, output_basedir, "snippet_%d_notes.dump" % (snippet['id'],))


def backup_issues(project, output_basedir):
    """
    Backup all issues of a project
    issue notes must be backuped by additional api call
    """
    issue_attachments = { "notes": NOTES_FOR_ISSUES,
                          "merge_requests" : MERGE_REQUESTS_FOR_ISSUES }

    log(u"Backing up issues from project %s [ID %s]" % (project['name'], project['id']))

    issues = fetch(PROJECT_COMPONENTS['issues'] % (API_BASE_URL, project['id']))

    dump(issues, output_basedir, "issues.json")

    for issue in issues:
        for (attachment, api_url) in issue_attachments.items():
            data = fetch(api_url % (API_BASE_URL, project['id'], issue['iid']))

            if data:
                dump(data, output_basedir, "issues_%d_%s.dump" % (issue['id'], attachment))


def backup_user_metadata(user, backup_dir=BACKUP_DIR):
    """
    Backup all metadata including email addresses and SSH keys of a single user
    """

    if not type(user) == dict:
        user = get_user(user)

    if user:
        output_basedir = os.path.join(backup_dir, "user_%s_%s" % (user['id'], user['username']))
        if not os.path.exists(backup_dir): os.mkdir(backup_dir)
        if not os.path.exists(output_basedir): os.mkdir(output_basedir)

        log(u"Backing up metadata of user %s [ID %s]" % (user["username"], user["id"]))
        dump(user, output_basedir, "user.json")
        dump(list(get_projects(user["username"])), output_basedir, "projects.json")
        dump(fetch(USER_SSHKEYS % (API_BASE_URL, user["id"])), output_basedir, "ssh.json")
        dump(fetch(USER_EMAILS % (API_BASE_URL, user["id"])), output_basedir, "email.json")


def backup_project(project, output_basedir, queue, archive=False):
    """
    Backup a single project
    """
    success = []

    if not os.path.exists(output_basedir): os.mkdir(output_basedir)

    dump(project, output_basedir, "project.json")
    backup_repository(project, output_basedir, resolve_lfs=archive)
    backup_local_data(project, output_basedir)

    # backup metadata of each component
    for (component, api_url) in PROJECT_COMPONENTS.items():
        # issues
        if component == "issues" and \
            project.get(component + "_enabled") == True:
            backup_issues(project, output_basedir)

        # snippets
        elif component == "snippets" and \
            project.get(component + "_enabled") == True:
            backup_snippets(project, output_basedir)

        # milestones are enabled if either issues or merge_requests are enabled
        # labels cannot be disabled therefore no labels_enabled field exists
        # otherwise check if current component is enabled in project
        elif component == "milestones" and \
             (project.get("issues_enabled") == True or project.get("merge_requests_enabled") == True):
            log(u"Backing up %s from project %s [ID %s]" % (component, project['name'], project['id']))
            dump(fetch(api_url % (API_BASE_URL, project['id'])),
                 output_basedir,
                 component + ".json")

        elif project.get(component + "_enabled") and project.get(component + "_enabled") == True:
            dump(fetch(api_url % (API_BASE_URL, project['id'])),
                 output_basedir,
                 component + ".json")

        elif component != "milestones" and \
             component != "snippets" and \
             component != "issues" and \
             project.get(component + "_enabled", "not_disabled") == "not_disabled":
            dump(fetch(api_url % (API_BASE_URL, project['id'])),
                 output_basedir,
                 component + ".json")


def backup(queue, backup_dir, archive=False):
    """
    Backup everything for the given project
    For every project create a dictionary with id_name as pattern
    Dump project metadata and each component as separate JSON files
    """
    while queue.qsize() > 0:
        project = queue.get()
        output_basedir = os.path.join(backup_dir, "%s_%s_%s" % (project['id'], project['namespace']['name'], project['name']))

        if not project.get("retried"):
            project["retried"] = 3

        try:
            backup_project(project, output_basedir, queue, archive)
        except (ArchiveError, CloneError, WebError) as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=3, file=sys.stdout)
            error(str(e))

            if project.get("retried") > 0:
                project["retried"] = project["retried"] - 1
                queue.put(project)
