#
# Central lib for Gitlab Tools
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

import json
import random
import string
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


def info(message):
    """
    Log an info message
    """
    log(message)


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
            response = requests.get(url, headers={"PRIVATE-TOKEN" : TOKEN})
        elif method == "PUT":
            response = requests.put(url, data=data, headers={"PRIVATE-TOKEN" : TOKEN})
        elif method == "DELETE":
            response = requests.delete(url, headers={"PRIVATE-TOKEN" : TOKEN})
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


def make_request(method="GET", rest_url=None, data={}, ignore_errors=False):
    """
    Make REST call and parse results
    Returns a list of dicts
    """
    result = []

    try:
        result = rest_api_call(rest_url, data=data, method=method).json()
    except (TypeError, ValueError) as e:
        if not ignore_errors:
            error("Call to url %s failed: %s\n" % (rest_url, str(e)))

    if type(result) == dict and result.get('message'):
        if not ignore_errors:
            error("Request to %s failed: %s\n" %(rest_url, result.get('message')))

        result = []

    return result


def fetch(rest_url, ignore_errors=False):
    """
    Fetch a REST URL with global private token and parse the resulting JSON
    Returns list of dictionaries

    >>> fetch("https://" + SERVER + "/api/v3/users/1")['name']
    u'Administrator'
    """

    return make_request("GET", rest_url, ignore_errors=ignore_errors)


def post(rest_url, post_data={}, ignore_errors=False):
    """
    Post a REST URL with global private token and given post data and parse the resulting JSON
    Returns list of dictionaries
    """

    return make_request("POST", rest_url, data=post_data, ignore_errors=ignore_errors)


def delete(rest_url, ignore_errors=False):
    """
    Delete a REST URL with global private token and given post data and parse the resulting JSON
    """

    return make_request("DELETE", rest_url, ignore_errors=ignore_errors)


def put(rest_url, put_data={}, ignore_errors=False):
    """
    PUT a REST URL with global private token and given post data and parse the resulting JSON
    """

    return make_request("PUT", rest_url, data=put_data, ignore_errors=ignore_errors)


def randompassword(min=8, max=12):
    """
    Guess what? Generates a random string :)
    """

    return ''.join([random.choice(string.printable) for _ in range(random.randint(min, max))])


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
    """
    Fetch a object with obj_id by REST call and return the given property
    """
    metadata = fetch("%s/%s/%d" % (API_URL, obj, obj_id))
    return metadata.get(obj_property)

def set_property(obj, obj_id, obj_property, obj_value):
    """
    Update property of object with obj_id by REST call
    """

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
    p.join()

    return p


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
