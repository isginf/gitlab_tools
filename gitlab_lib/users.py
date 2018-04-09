#
# Central lib for Gitlab Tools - User code
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

from .core import *
from .api import *
from .exception import APIError


#
# SUBROUTINES
#

def user_involved_in_project(username, project):
    """
    Returns true if username is somehow involved in project
    Project must be dict returned by REST API
    """
    involved = None

    try:
        involved = project['namespace']['name'] == username or \
                   (project.get("owner") and project.get('owner').get('username') == username) or \
                   username in [x.get('username') for x in fetch(PROJECT_MEMBERS % (API_BASE_URL, project["id"]), ignore_errors=True)]

        if not involved and project["namespace"]["kind"] == "group":
            involved = username in [x.get('username') for x in fetch(GROUP_MEMBERS % (API_BASE_URL, project["namespace"]["id"]), ignore_errors=True)]
    except AttributeError as e:
        raise APIError("user_involved_in_project", "Got unexpected results for %s - %s\nException was %s" % (username, str(project), str(e)))

    return involved


def __username_filter(user, usernames_only=False):
    if usernames_only:
        return user["username"]
    else:
        return user


def __user_provider_matches(user, provider):
    result = False

    for identity in user.get("identities"):
        if identity.get("provider") in provider:
            result = True

    return result


def create_user(username=None, name=None, email=None, metadata={}):
    """
    Create a new user with the given data
    Return user details as json
    """

    metadata["name"] = name
    metadata["username"] = username
    metadata["email"] = email

    user= post(CREATE_USER % (API_BASE_URL,), metadata)

    return user


def delete_user(user):
    """
    Deletes the user with the given name or id
    """

    if not type(user) == dict:
        user = get_user(user)

    return delete(DELETE_USER % (API_BASE_URL, user["id"]), {"id": user["id"]})


def get_users(chunk_size=100, provider=None, state=None, usernames_only=False):
    """
    Returns a generator for all gitlab users
    Parameter provider (e.g. ldap or google_oauth2) can be string or list
    state like active or blocked can also be string or list
    If you don't need user objects but only usernames set usernames_only to True

    >>> len(list(get_users())) > 0
    True
    """
    page = 1

    if not type(state) == list:
        state = [state]

    if not type(provider) == list:
        provider = [provider]

    while 1:
        buff = fetch(GET_NO_OF_USERS % (API_BASE_URL, chunk_size, page))

        if buff:
            for user in buff:
                if (not provider[0] or __user_provider_matches(user, provider)) and \
                   (not state[0] or user.get("state") in state):
                    yield __username_filter(user, usernames_only)

            page += 1

        else:
            break


def get_user(username=None):
    """
    Get metadata of a single user
    """
    result = fetch(USER_BY_USERNAME % (API_BASE_URL, username))

    if result:
        return result[0]
    else:
        return None


def __block_or_unblock(url, user):
    """
    Internal helper function to block or unblock a user
    """
    result = None

    try:
        result = rest_api_call(url % (API_BASE_URL, int(user)), {"id": int(user)}, method="POST")
    except ValueError:
        pass

    if not result:
        user_dict = get_user(user)

        if user_dict:
            result = rest_api_call(url % (API_BASE_URL, user_dict["id"]), {"id": user_dict["id"]}, method="POST")

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


def convert_user_to_id(user):
    """
    Try to use user as id (int)
    Otherwise fetch user by name
    """
    try:
        user_id = int(user)
    except (TypeError, ValueError):
        user_id = fetch(USER_BY_USERNAME % (API_BASE_URL, user))[0].get("id")

    return user_id
