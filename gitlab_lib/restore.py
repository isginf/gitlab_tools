#
# Central lib for Gitlab Tools - Restore code
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
import shutil
import tarfile
import tempfile
import subprocess
import gitlab_lib
from pipes import quote
from .core import *
from .api import *
from .projects import *
from .namespaces import *
from gitlab_config import TMP_DIR, GITLAB_DIR


#
# SUBROUTINES
#

def prepare_restore_data(project_id, entry):
    """
    Set project id as id on entry data, remove every unwanted key and add
    required key with default values

    >>> prepare_restore_data(42, {'title': 'test', 'component': 'issues'})
    {'id': '42', 'title': 'test'}
    """
    unwanted = ["component",
                "created_at",
                "updated_at",
                "expires_at",
                "web_url"
                "merge_when_pipeline_succeeds",
                "work_in_progress",
                "user_notes_count",
                "upvotes"]

    entry["id"] = str(project_id)

    return { k: v for (k, v) in entry.items() if k not in unwanted }


def __get_entry_id(entry, created_entry):
    """
    Helper function - Some entries are updated with iid instead of id
    """
    entry_id = entry['id']

    if (entry['component'] == "issues" or \
       entry['component'] == "merge_requests") and \
       created_entry.get('iid'):
            entry_id = created_entry['iid']
    elif created_entry.get('id'):
        entry_id = created_entry['id']

    return entry_id


def close_entry_if_needed(entry, created_entry, project_id):
    """
    Some components have a state closed like issues or merge requests
    Check if we have an edit api url and execute it
    entry is a dictionary with all data of entry, created_entrya http response dict from entry creation
    """
    try:
        edit_url = getattr(gitlab_lib.api, entry['component'].upper() + "_EDIT")

        if edit_url and entry.get('state') == 'closed':
            if entry['component'] == "issues":
                entry['issue_iid'] = entry['iid']

            elif entry['component'] == "merge_requests":
                entry['merge_request_iid'] = entry['iid']

            rest_api_call(edit_url % (API_BASE_URL, project_id, __get_entry_id(entry, created_entry)),
                          prepare_restore_data(project_id, entry),
                          "PUT")
    except AttributeError:
        pass


def restore_repository(backup_archive, repository_base_dir, project_name, suffix=".git"):
    """
    Unpack archive to tmp dir, convert to bare repo, move it to repo dir
    and create link to global gitlab hooks dir
    Clear Redis cache afterwards to refresh the dashboard
    """
    tar = tarfile.open(backup_archive, "r:gz")

    tmp_dir = tempfile.TemporaryDirectory(dir=TMP_DIR)
    repository_dest = os.path.join(repository_base_dir, project_name + suffix)

    # unpack repo
    tar.extractall(tmp_dir.name)
    os.chdir(os.path.dirname(tmp_dir.name))

    # remove lfs config
    if os.path.exists(os.path.join(tmp_dir.name, ".gitattributes")):
        log("Removing .gitattributes file")
        os.unlink(os.path.join(tmp_dir.name, ".gitattributes"))

    # convert to bare repo
    subprocess.call(["git", "clone", "--bare", os.path.basename(tmp_dir.name)])
    os.chdir(tmp_dir.name + ".git")

    # remove origin as its the tmp dir
    subprocess.call(["git", "remote", "rm", "origin"])
    os.chdir(os.path.dirname(tmp_dir.name))

    if os.path.exists(repository_dest):
        shutil.rmtree(repository_dest)

    # move restored repo to repo path
    shutil.move(tmp_dir.name + ".git", repository_dest)

    # install global gitlab hooks
    shutil.rmtree(os.path.join(repository_dest, "hooks"))
    os.symlink(os.path.join(GITLAB_DIR, "embedded","service","gitlab-shell","hooks"),
               os.path.join(repository_dest, "hooks"))

    tmp_dir.cleanup()

    # reset dashboard
    subprocess.call(["gitlab-rake", "cache:clear"])


def restore_project(backup_dir, project_name, namespace_name=None):
    """
    Create the project, add it's members and activate components
    Returns project metadata as dictionary
    """
    project = {}
    namespace_id = None

    project_data = parse_json(os.path.join(backup_dir, "project.json"))

    if namespace_name:
        tmp = gitlab_lib.get_namespaces(namespace_name)

        if not tmp or len(tmp) == 0:
            raise ValueError("Cannot find namespace " + namespace_name)
        elif len(tmp) > 1:
            raise ValueError("Found more than one entry for namespace " + namespace_name)
        else:
            namespace_id = tmp[0]["id"]
    else:
        namespace_name = project_data['namespace']['name']
        namespace_id = project_data['namespace']['id']

    project_data['name'] = project_name
    project_data['path'] = project_name
    project_data['name_with_namespace'] = namespace_name + " / " + project_name
    project_data['path_with_namespace'] = namespace_name + "/" + project_name
    project_data['lfs_enabled'] = False

    del project_data['id']
    del project_data['ssh_url_to_repo']
    del project_data['last_activity_at']
    del project_data['http_url_to_repo']
    del project_data['_links']

    project_data['namespace_id'] = namespace_id
    del project_data['namespace']

    project = create_project(project_name, prepare_restore_data(project_data.get('id'), project_data))

    members = parse_json(os.path.join(backup_dir, "members.json"))

    for member in members:
        log("Adding member %s" % (member['username'],))
        add_project_member(project['id'], member['id'], member['access_level'])

    return project


def restore_entry(backup_dir, project, entry):
    """
    Restore a single entry of a project component
    """
    log("Restoring %s [%s]" % (entry['component'], entry.get('name') or "ID " + str(entry.get('id'))))

    # for merge requests we must update source and target project id
    if entry['component'] == "merge_requests":
        if entry['source_project_id'] == entry['target_project_id']:
            entry['source_project_id'] = entry['project_id']

        entry['target_project_id'] = entry['project_id']

    # for snippets we must additionally restore the content file
    if entry['component'] == "snippets":
        restore_snippets(backup_dir, project, entry)
    else:
        entry = update_metadata(entry)

        # If we restore issues, check if the issue had an attached merge request
        # merge request was restored beforehand and the iid must be lookuped with its global id
        if entry['component'] == "issues":
            merge_request = get_merge_request_for_issue(backup_dir, project, entry['id'])
            entry['merge_request_to_resolve_discussions_of'] = merge_request.get('iid')

        result = rest_api_call(PROJECT_COMPONENTS[entry['component']] % (API_BASE_URL, project['id']),
                               prepare_restore_data(project['id'], entry)).json()

        close_entry_if_needed(entry, result, project['id'])

        # some components have notes attached. check if we have an edit api url and execute it
        try:
            if getattr(gitlab_lib.api, "NOTES_FOR_" + entry['component'].upper()):
                restore_notes(backup_dir,
                              getattr(gitlab_lib.api, "NOTES_FOR_" + entry['component'].upper()) % (API_BASE_URL, project['id'], __get_entry_id(entry, result)),
                              project,
                              entry)
        except AttributeError:
            pass


def restore(backup_dir, project, work_queue):
    """
    Restore a projects components
    """
    while work_queue.qsize() > 0:
        entry = work_queue.get()
        restore_entry(backup_dir, project, entry)


def restore_snippets(backup_dir, project, entry):
    """
    Restore a single snippet
    """
    if not entry.get('visibility_level'):
        entry['visibility_level'] = VISIBILITY_PRIVATE

    if not entry.get('file_name'):
        entry['file_name'] = quote(entry['title']).replace(" ", "_").replace("'", "") + ".txt"

        snippet_content = os.path.join(backup_dir, "snippet_" + str(entry.get('id')) + "_content.dump")
        entry['code'] = parse_json(snippet_content)

        if entry['code']:
            debug("RESTORE ENTRY\n\tcomponent %s\n\turl %s\n\tproject %s\n\tentry %s\n" % (entry['component'],
                                                                                           PROJECT_COMPONENTS[entry['component']],
                                                                                           project['id'],
                                                                                           prepare_restore_data(project['id'], entry)))

            result = rest_api_call(PROJECT_COMPONENTS["snippets"] % (API_BASE_URL, project['id']),
                                   prepare_restore_data(project['id'], entry)).json()

            restore_notes(backup_dir,
                          NOTES_FOR_SNIPPET % (API_BASE_URL, project['id'], __get_entry_id(entry, result)),
                          project,
                          entry)
        else:
            error("Content file of snippet " + str(entry.get('id')) + " cannot be found. Won't restore snippet!")


def restore_notes(backup_dir, api_url, project, entry):
    """
    Restore the notes to a component like snippets or issues
    """
    notes_file = os.path.join(backup_dir, entry['component'] + "_" + str(entry.get('id')) + "_notes.dump")

    if os.path.exists(notes_file):
        notes = parse_json(notes_file)

        for note in notes:
            note[entry['component'] + '_id'] = str(entry.get('id'))

            rest_api_call(api_url, prepare_restore_data(project['id'], note))


def get_merge_request_for_issue(backup_dir, project, issue_id):
    """
    Check if there is a merge request related to the given issue_id
    """
    result = {}
    merge_requests_file = os.path.join(backup_dir, "issues_" + str(issue_id) + "_merge_requests.dump")

    if os.path.exists(merge_requests_file):
        merge_requests = parse_json(merge_requests_file)

        if merge_requests and len(merge_requests) > 0:
            result = merge_requests[0]

    return result


def update_metadata(entry):
    """
    Set owner and assignee, close the ticket/merge_request if it was closed
    """

    if entry.get('state') == "closed":
        entry['state_event'] = "close"

    # TODO: deprecated
    if entry.get('assignee'):
        entry['assignee_id'] = entry['assignee']['id']
        del entry['assignee']

    if entry.get('assignees'):
        entry['assignee_ids'] = [x.get('id') for x in entry['assignees']]
        del entry['assignees']

    if entry.get('author'):
        entry['author_id'] = entry['author']['id']
        del entry['author']

    if entry.get('milestone'):
        entry['milestone_id'] = entry['milestone']['id']
        del entry['milestone']

    return entry
