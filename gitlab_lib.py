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
    "issues": "%s/projects/%s/issues",
    "snippets": "%s/projects/%s/snippets",
    "labels": "%s/projects/%s/labels",
    "milestones": "%s/projects/%s/milestones",
    "merge_requests": "%s/projects/%s/merge_requests"
}

PROJECT_MEMBERS = "%s/projects/%d/members"
PROJECT_METADATA = "%s/projects/%d"
PROJECT_SEARCH = "%s/projects?search=%s"
ISSUE_EDIT = "%s/projects/%s/issues/%s"
GET_NO_OF_PROJECTS = "%s/projects/all?per_page=%d&page=%d"
GET_SNIPPET_CONTENT = "%s/projects/%d/snippets/%d/raw"
NOTES_FOR_SNIPPET = "%s/projects/%s/snippets/%s/notes"
NOTES_FOR_ISSUE = "%s/projects/%s/issues/%s/notes"


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


def fetch(rest_url):
    """
    Fetch a REST URL with global private token and parse the resulting JSON
    Returns list of dictionaries

    >>> fetch("https://" + SERVER + "/api/v3/users/1")['name']
    u'Administrator'
    """
    result = None

    try:
        result = rest_api_call(rest_url, TOKEN, method="GET").json()
    except TypeError as e:
        error("Failed parsing JSON of url %s error was %s\n" % (rest_url, str(e)))

    return result


def get_projects():
    """
    Returns a list of all gitlab projects if not otherwise specified

    >>> len(get_projects()) > 0
    True
    """
    projects = []
    chunk_size = 100
    page = 1

    while 1:
        buff = fetch(GET_NO_OF_PROJECTS % (API_URL, chunk_size, page))

        if buff:
            projects.extend(buff)
            page += 1
        else:
            break

    return projects


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
