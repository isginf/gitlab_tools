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

import os
import json
import random
import string
import datetime
import requests
from multiprocessing import Process
from .api import API_BASE_URL
from .exception import WebError, ReadError, ParseError
from gitlab_config import SERVER, TOKEN, CLONE_ACCESS_TOKEN, REPOSITORY_DIR, BACKUP_DIR, UPLOAD_DIR, TMP_DIR, ERROR_LOG, LOG_ERRORS, LOG_TIMESTAMP, TAR_TIMEOUT, GIT_TIMEOUT, API_TIMEOUT

#
# Configuration
#

QUIET=False
DEBUG=False


#
# Subroutines
#

def log_prefix():
    ts = datetime.datetime.now().strftime(LOG_TIMESTAMP)

    if DEBUG:
        return "\n[%d]-[%s]\n\t" % (os.getpid(), ts)
    else:
        return ""


def log(message):
    """
    Log a message to STDOUT
    """
    if not QUIET:
        print("%s%s" % (log_prefix(), message))


def error(message):
    """
    Log an error message
    """
    print("%s>>> ERROR: %s" % (log_prefix(), message))

    if LOG_ERRORS:
        with open(ERROR_LOG, "a") as err:
            ts = datetime.datetime.now().strftime(LOG_TIMESTAMP)
            err.write("[%s] %s\n" % (ts, message))


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
    error_msg = None

    try:
        debug(method + "\n\turl " + url + "\n\tdata " + str(data) + "\n")

        if method == "GET":
            response = requests.get(url, headers={"PRIVATE-TOKEN" : TOKEN}, timeout=API_TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, data=data, headers={"PRIVATE-TOKEN" : TOKEN}, timeout=API_TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, headers={"PRIVATE-TOKEN" : TOKEN}, timeout=API_TIMEOUT)
        else:
            response = requests.post(url, data=data, headers={"PRIVATE-TOKEN" : TOKEN}, timeout=API_TIMEOUT)
    except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
        error_msg = "Request to url %s failed: %s" % (url, str(e))
        response = None
    except requests.exceptions.Timeout as e:
        error_msg = "Request to url %s timedout: %s\n%s" % (url, response.text, str(e))


    if response and response.status_code == 401:
        error("Request to url %s unauthorized! %s" % (url, response.text))
        response = None

    if type(response) == dict and response.get('message'):
        error("Request to url %s failed! %s" % (url, response.get('message')))
        response = None

    elif type(response) == dict and response.get('error'):
        error("Request to url %s failed! %s" % (url, response.get('error')))
        response = None

    if response:
        debug("RESPONSE " + str(response.status_code) + " " + response.text)
    else:
        debug("NO RESPONSE")

    if error_msg:
        error("ERROR " + error_msg)
        raise WebError(url, data, method, error_msg)

    return response


def make_request(method="GET", rest_url=None, data={}, ignore_errors=False):
    """
    Make REST call and parse results
    Returns a list of dicts
    """
    result = []

    try:
        result = rest_api_call(rest_url, data=data, method=method)
 
        if not method == "DELETE":
            result = result.json()

    except (TypeError, ValueError) as e:
        if not ignore_errors:
            raise WebError(rest_url, data, method, "Call to url %s failed: %s\n" % (rest_url, str(e)))

#    if type(result) == dict and result.get('message'):
#        if not ignore_errors:
#            raise WebError(rest_url, data, method, "Request to %s failed: %s\n" % (rest_url, result.get('message')))
#
#        result = []

    if type(result) == str:
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


def fetch_per_page(api_url, chunk_size=100, filter_func=None):
    """
    Fetch data from an api url until it returns empty list
    api_url must have placeholder per_page=%d&page=%d
    chunk_size defines number of per page
    filter_func can be used to filter the result
    """
    page = 1

    while 1:
        buffer = fetch(api_url % (API_BASE_URL, chunk_size, page))

        if buffer:
            if filter_func:
                buffer = filter(filter_func, buffer)

            page += 1

            for chunk in buffer:
                yield chunk
        else:
            return


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


def get_property(obj, obj_id, obj_property):
    """
    Fetch a object with obj_id by REST call and return the given property
    """
    metadata = fetch("%s/%s/%d" % (API_BASE_URL, obj, obj_id))
    return metadata.get(obj_property)


def set_property(obj, obj_id, obj_property, obj_value):
    """
    Update property of object with obj_id by REST call
    """

    rest_url = "%s/%s/%d" % (API_BASE_URL, obj, obj_id)

    try:
        result = rest_api_call(rest_url, {obj_property: obj_value}, method="PUT")
    except TypeError as e:
        error("Failed parsing JSON of url %s error was %s\n" % (rest_url, str(e)))

    return result


def create_process(func, args):
    """
    Create and start a new subprocess
    """
    p = Process(target=func, args=args)
    p.daemon = True
    p.start()

    return p


def parse_json(json_file):
    """
    Parse a JSON file
    """
    data = None

    try:
        raw_data = open(json_file, "rb").read().decode('utf8')
        data = json.loads(raw_data)
    except IOError as e:
        raise ReadError(json_file, str(e))
    except ValueError as e:
        raise ParseError(json_file, str(e))

    return data
