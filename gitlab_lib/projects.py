#
# Central lib for Gitlab Tools - Projects code
#
# Copyright 2018 ETH Zurich, ISGINF, Bastian Ballmann
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

from .core import *
from .api import *
from . import permissions
from .users import convert_user_to_id, user_involved_in_project


#
# SUBROUTINES
#

def create_project(name=None, metadata={}):
    """
    Create a new project with the given data
    Return project details as json
    """

    metadata["name"] = name

    project = post(CREATE_PROJECT % (API_BASE_URL,), metadata)

    return project


def delete_project(project):
    """
    Deletes the project with the given name or id
    """

    project_data = get_project_metadata(project)

    if len(project_data) == 0:
        raise ValueError("Unknown project " + project)
    elif len(project_data) > 1:
        raise ValueError("Found more than one project " + project)

    return delete(DELETE_PROJECT % (API_BASE_URL, project_data[0]["id"]))


def get_projects(username=None, personal=False, only_archived=False):
    """
    Returns a list of all gitlab projects
    If username was specified returns list of projects user is involved in
    If personal is true only personal projects of the given user are returned
    Set only_archived to True if you only want to see archived projects

    >>> len(get_projects()) > 0
    True
    """
    chunk_size = 100
    api_url = GET_NO_OF_PROJECTS
    filter_func = None

    if username:
        if personal:
            filter_func = lambda x: x['namespace']['name'] == username
        else:
            filter_func = lambda x: user_involved_in_project(username, x)

    if only_archived:
        api_url = GET_ARCHIVED_PROJECTS

    for project in fetch_per_page(api_url, chunk_size, filter_func):
        yield project


def get_project(project):
    project = get_project_metadata(project)

    if len(project) == 0:
        return {}
    else:
        return project[0]

def get_project_metadata(project):
    """
    project can be id or name
    returns list of found projects and their metadata as dictionary

    >>> type(get_project_metadata(2)[0]) == dict
    True
    """
    data = []

    if type(project) == dict:
        data.append(project)
    else:
        try:
            data.append( fetch(PROJECT_METADATA % (API_BASE_URL, int(project))) )
        except ValueError:
            projects = fetch(PROJECT_SEARCH % (API_BASE_URL, project))

            if len(projects) > 0:
                data.append( fetch(PROJECT_METADATA % (API_BASE_URL, int(projects[0]["id"]))) )

    return data


def get_project_members(project_id):
    """
    Get all members of the given project id
    Returns a list of dictionaries
    """

    return fetch(PROJECT_MEMBERS % (API_BASE_URL, project_id))


def add_project_member(project_id, user, access_level=permissions.ACCESS_LEVEL_GUEST):
    """
    Add a member with the given access_level to the specified project id
    """
    return post(ADD_PROJECT_MEMBER % (API_BASE_URL, project_id), {"id": project_id,
                                                             "user_id": convert_user_to_id(user),
                                                             "access_level": access_level})


def edit_project_member(project_id, user, access_level, expires_at=None):
    """
    Change the member properties of the given user on the project
    User can be username or id, project must be id and access level must be given
    """

    user_id = convert_user_to_id(user)
    data = {"id": project_id,
            "user_id": user_id,
            "access_level": access_level}

    if expires_at:
        data["expires_at"] = expires_at

    return put(EDIT_PROJECT_MEMBER % (API_BASE_URL, project_id, user_id), data)



def delete_project_member(project_id, user):
    """
    Delete the given user from the project
    User can be username or id, project must be id
    """

    return delete(DEL_PROJECT_MEMBER % (API_BASE_URL, project_id), {"id": project_id,
                                                               "user_id": convert_user_to_id(user)})

def protect_branch(project_id, branch="master"):
    """
    Protect the specified branch of the given project id
    """
    return put(PROTECT_BRANCH % (API_BASE_URL, project_id, branch), ignore_errors=True)
