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
import gitlab_lib
from pipes import quote
from .core import *
from .api import *


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
                "merge_when_pipeline_succeeds",
                "work_in_progress",
                "user_notes_count",
                "upvotes"]

    entry["id"] = str(project_id)

    return { k: v for (k, v) in entry.items() if k not in unwanted }


def __get_entry_id(entry, entry_id):
    """
    Helper function - Some entries are updated with iid instead of id
    """
    if entry['component'] == "issues" or \
       entry['component'] == "merge_requests":
        entry_id = entry['iid']

    return entry_id


def close_entry_if_needed(entry, entry_id, project_id):
    """
    Some components have a state closed like issues or merge requests
    Check if we have an edit api url and execute it
    entry is a dictionary with all data of entry, entry_id the id of the entry to close
    """
    try:
        if entry.get('state') == 'closed' and getattr(gitlab_lib.api, entry['component'].upper() + "_EDIT"):
            if entry['component'] == "issues":
                entry['issue_iid'] = entry['iid']

            elif entry['component'] == "merge_requests":
                entry['merge_request_iid'] = entry['iid']

            rest_api_call(getattr(gitlab_lib.api, entry['component'].upper() + "_EDIT") % (API_BASE_URL, project_id, __get_entry_id(entry, entry_id)),
                          prepare_restore_data(project_id, entry),
                          "PUT")
    except AttributeError:
        pass


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

        if entry['component'] == "issues":
            entry['merge_request_to_resolve_discussions_of'] = get_merge_request_for_issue(backup_dir, project, entry['id']).get('id')

        result = rest_api_call(PROJECT_COMPONENTS[entry['component']] % (API_BASE_URL, project['id']),
                               prepare_restore_data(project['id'], entry)).json()

        close_entry_if_needed(entry, result.get('id'), project['id'])

        # some components have notes attached. check if we have an edit api url and execute it
        try:
            if getattr(gitlab_lib.api, "NOTES_FOR_" + entry['component'].upper()):
                restore_notes(backup_dir,
                              getattr(gitlab_lib.api, "NOTES_FOR_" + entry['component'].upper()) % (API_BASE_URL, project['id'], __get_entry_id(entry, result['id'])),
                              project,
                              entry)
        except AttributeError:
            pass


def restore(backup_dir, project, queue):
    """
    Restore a project
    """
    while not queue.empty():
        entry = queue.get()
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

            rest_api_call(PROJECT_COMPONENTS["snippets"] % (API_BASE_URL, project['id']),
                          prepare_restore_data(project['id'], entry))

            restore_notes(backup_dir,
                          NOTES_FOR_SNIPPET % (API_BASE_URL, project['id'], str(entry.get('id'))),
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
