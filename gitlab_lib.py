#
# Central lib for Gitlab Tools
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
# Loading modules
#

import sys
sys.path.append("..")

import json
import requests
from multiprocessing import Process
from backup_config import SERVER, TOKEN


#
# Configuration
#

QUIET=False
DEBUG=False


#
# API
#

API_URL = "https://%s/api/v3" % (SERVER,)

PROJECT_COMPONENTS = {
    "request_access": "%s/projects/%s/access_requests",
    "boards": "%s/projects/%s/boards",
    "issues": "%s/projects/%s/issues",
    "labels": "%s/projects/%s/labels",
    "members": "%s/projects/%s/members",
    "milestones": "%s/projects/%s/milestones",
    "merge_requests": "%s/projects/%s/merge_requests",
    "snippets": "%s/projects/%s/snippets"
}

PROJECT_MEMBERS = "%s/projects/%d/members"
PROJECT_METADATA = "%s/projects/%d"
PROJECT_SEARCH = "%s/projects?search=%s"
GET_NO_OF_USERS = "%s/users?per_page=%d&page=%d"
USER_METADATA = "%s/users/%s"
USER_BY_USERNAME = "%s/users?username=%s"
USER_SSHKEYS = "%s/users/%s/keys"
USER_EMAILS = "%s/users/%s/emails"
GROUP_MEMBERS = "%s/groups/%s/members"
ISSUE_EDIT = "%s/projects/%s/issues/%s"
GET_NO_OF_PROJECTS = "%s/projects/all?per_page=%d&page=%d"
GET_SNIPPET_CONTENT = "%s/projects/%d/snippets/%d/raw"
NOTES_FOR_SNIPPET = "%s/projects/%s/snippets/%s/notes"
NOTES_FOR_ISSUE = "%s/projects/%s/issues/%s/notes"
BLOCK_USER = "%s/users/%s/block"
UNBLOCK_USER = "%s/users/%s/unblock"


#
# Subroutines
#

def log(message):
    """
    Log a message to STDOUT
    """
    if not QUIET:
        print(message)

def error(message):
    """
    Log an error message
    """
    log(">>> ERROR: " + message)


def debug(message):
    """
    Log a debug message
    """
    if DEBUG:
        log("DEBUG: " + message)


def rest_api_call(url, data={}, method="POST"):
    """
    POST or PUT data dictionary to URL
    Returns: request Response object

    >>> rest_api_call("https://" + SERVER + "/api/v3/projects/2/issues", {"id": 2, "title": "just a test"}).json()['title']
    u'just a test'
    """
    try:
        debug(method + "\n\turl " + url + "\n\tdata " + str(data) + "\n")

        if method == "GET":
            response = requests.get(url, data=data, headers={"PRIVATE-TOKEN" : TOKEN})
        elif method == "PUT":
            response = requests.put(url, data=data, headers={"PRIVATE-TOKEN" : TOKEN})
        else:
            response = requests.post(url, data=data, headers={"PRIVATE-TOKEN" : TOKEN})
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
        error("Request to url %s failed: %s" % (url, str(e)))
        response = None
    except requests.exceptions.Timeout as e:
        error("Request to url %s timedout: %s" % (url, str(e)))
        response = None

    if response.status_code == 401:
        error("Request to url %s unauthorized! %s" % (url, response.text))
        response = None

    if response:
        debug("RESPONSE " + str(response.status_code) + " " + response.text + "\n")

    return response


def fetch(rest_url, ignore_errors=False):
    """
    Fetch a REST URL with global private token and parse the resulting JSON
    Returns list of dictionaries

    >>> fetch("https://" + SERVER + "/api/v3/users/1")['name']
    u'Administrator'
    """
    result = []

    try:
        result = rest_api_call(rest_url, TOKEN, method="GET").json()
    except (TypeError, ValueError) as e:
        if not ignore_errors:
            error("Call to url %s failed: %s\n" % (rest_url, str(e)))

    if type(result) == dict and result.get('message'):
        if not ignore_errors:
            error("Request to %s failed: %s\n" %(rest_url, result.get('message')))

        result = []

    return result


def user_involved_in_project(username, project):
    """
    Returns true if username is somehow involved in project
    Project must be dict returned by REST API
    """
    return project['namespace']['name'] == username or \
        (project.get("owner") and project.get('owner').get('username') == username) or \
        username in [x.get('username') for x in fetch(PROJECT_MEMBERS % (API_URL, project["id"]), ignore_errors=True)] or \
        username in [x.get('username') for x in fetch(GROUP_MEMBERS % (API_URL, project["namespace"]["id"]), ignore_errors=True)]



def __username_filter(user, usernames_only=False):
    if usernames_only:
        return user["username"]
    else:
        return user


def __user_provider_matches(user, provider):
    result = False

    for identity in user.get("identities"):
        if identity.get("provider") == provider:
            result = True

    return result


def get_users(chunk_size=100, provider=None, state=None, usernames_only=False):
    """
    Returns a generator for all gitlab users

    >>> len(list(get_users())) > 0
    True
    """
    page = 1

    while 1:
        buff = fetch(GET_NO_OF_USERS % (API_URL, chunk_size, page))

        if buff:
            for user in buff:
                if (provider and (not user.get("identities") or __user_provider_matches(user, provider))) and \
                   (state and user.get("state") == state):
                    yield __username_filter(user, usernames_only)

            page += 1

        else:
            break


def get_projects(username=None, personal=False):
    """
    Returns a list of all gitlab projects
    If username was specified returns list of projects user is involved in
    If personal is true only personal projects of the given user are returned

    >>> len(get_projects()) > 0
    True
    """
    chunk_size = 100
    page = 1

    while 1:
        projects = fetch(GET_NO_OF_PROJECTS % (API_URL, chunk_size, page))

        if projects:
            if username:
                if personal:
                    projects = filter(lambda x: x['namespace']['name'] == username, buff)
                else:
                    projects = filter(lambda x: user_involved_in_project(username, x), buff)

            page += 1

            for project in projects:
                yield project
        else:
            return


def get_project_metadata(project):
    """
    project can be id or name
    returns list of found projects and their metadata as dictionary

    >>> type(get_project_metadata(2)[0]) == dict
    True
    """
    data = []

    try:
        data.append( fetch(PROJECT_METADATA % (API_URL, int(project))) )
    except ValueError:
        data.append( fetch(PROJECT_METADATA % (API_URL, project)) )

    return data


def get_user_metadata(user):
    """
    user can be name or id
    returns metadata of that single user

    >>> type(get_user_metadata(2)[0]) == dict
    >>> len(get_user_metadata(2)) == 1
    True
    """
    data = None

    try:
        data = fetch(USER_METADATA % (API_URL, int(user)))
    except ValueError:
        data = fetch(USER_BY_USERNAME % (API_URL, user))

    if len(data) > 0:
        return data[0]
    else:
        print("User " + user + " not found.")
        return {}


def __block_or_unblock(url, user):
    """
    Internal helper function to block or unblock a user
    """
    result = None

    try:
        result = rest_api_call(url % (API_URL, int(user)), {"id": int(user)}, method="PUT")
    except ValueError:
        pass

    if not result:
        user_dict = get_user_metadata(user)

        if user_dict:
            result = rest_api_call(url % (API_URL, user_dict["id"]), {"id": user_dict["id"]}, method="PUT")

    return result


def block_user(user):
    """
    Block the given user
    User can be id or name
    """
    return __block_or_unblock(BLOCK_USER, user)


def unblock_user(user):
    """
    Unlock the given user
    User can be id or name
    """
    return __block_or_unblock(UNBLOCK_USER, user)


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


def get_property(obj, obj_id, obj_property):
    metadata = fetch("%s/%s/%d" % (API_URL, obj, obj_id))
    return metadata.get(obj_property)

def set_property(obj, obj_id, obj_property, obj_value):
    rest_url = "%s/%s/%d" % (API_URL, obj, obj_id)

    try:
        result = rest_api_call(rest_url, {obj_property: obj_value}, method="PUT")
    except TypeError as e:
        print("Failed parsing JSON of url %s error was %s\n" % (rest_url, str(e)))

    return result


def create_process(func, args):
    """
    Create and start a new subprocess
    """
    p = Process(target=func, args=args)
    p.start()


def parse_json(json_file):
    """
    Parse a JSON file
    """
    data = None

    try:
        data = json.loads(open(json_file, "rb").read().decode('utf8'))
    except IOError as e:
        error("Cannot read %s: %s" % (json_file, str(e)))
    except ValueError as e:
        error("Cannot parse JSON file %s: %s" % (json_file, str(e)))

    return data
