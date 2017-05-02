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
from pipes import quote
from .core import *
from .api import *


#
# SUBROUTINES
#

def prepare_restore_data(project, entry):
    """
    Set project id as id on entry data, remove every unwanted key and add
    required key with default values

    >>> prepare_restore_data({'id': 42}, {'title': 'test', 'component': 'issues'})
    {'id': '42', 'title': 'test'}
    """
    unwanted = ["component", "created_at", "updated_at", "expires_at"]

    entry["id"] = str(project['id'])

    return { k: v for (k, v) in entry.items() if k not in unwanted }


def restore_entry(backup_dir, project, entry):
    """
    Restore a single entry of a project component
    """
    log("Restoring %s [%s]" % (entry['component'], entry.get('name') or "ID " + str(entry.get('id'))))

    # for snippets we must additionally restore the content file
    if entry['component'] == "snippets":
        restore_snippets(backup_dir, project, entry)
    else:
        result = rest_api_call(PROJECT_COMPONENTS[entry['component']] % (API_URL, project['id']),
                                          prepare_restore_data(project, entry))

        if entry['component'] == "issues":
            result = result.json()
            rest_api_call(ISSUE_EDIT % (API_URL, project['id'], result.get('id')),
                                     prepare_restore_data(project, update_issue_metadata(entry)),
                                     "PUT")
            restore_notes(backup_dir,
                          NOTES_FOR_ISSUE % (API_URL, project['id'], str(entry.get('id'))),
                          project,
                          entry)


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
                                                                                           prepare_restore_data(project, entry)))

            rest_api_call(PROJECT_COMPONENTS["snippets"] % (API_URL, project['id']),
                          prepare_restore_data(project, entry))

            restore_notes(backup_dir,
                          NOTES_FOR_SNIPPET % (API_URL, project['id'], str(entry.get('id'))),
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

            rest_api_call(api_url, prepare_restore_data(project, note))


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
