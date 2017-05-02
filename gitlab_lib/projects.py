#
# Central lib for Gitlab Tools - Projects code
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

    project = post(CREATE_PROJECT % (API_URL,), metadata)

    return project


def delete_project(project):
    """
    Deletes the project with the given name or id
    """

    if not type(project) == dict:
        project = get_project_metadata(project)

    return delete(DELETE_PROJECT % (API_URL, project["id"]))


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
                    projects = filter(lambda x: x['namespace']['name'] == username, projects)
                else:
                    projects = filter(lambda x: user_involved_in_project(username, x), projects)

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


def get_project_members(project_id):
    """
    Get all members of the given project id
    Returns a list of dictionaries
    """

    return fetch(PROJECT_MEMBERS % (API_URL, project_id))


def add_project_member(project_id, user, access_level=permissions.ACCESS_LEVEL_GUEST):
    """
    Add a member with the given access_level to the specified project id
    """
    return post(ADD_PROJECT_MEMBER % (API_URL, project_id), {"id": project_id,
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

    return put(EDIT_PROJECT_MEMBER % (API_URL, project_id, user_id), data)



def delete_project_member(project_id, user):
    """
    Delete the given user from the project
    User can be username or id, project must be id
    """

    return delete(DEL_PROJECT_MEMBER % (API_URL, project_id), {"id": project_id,
                                                               "user_id": convert_user_to_id(user)})

def protect_branch(project_id, branch="master"):
    """
    Protect the specified branch of the given project id
    """
    return put(PROTECT_BRANCH % (API_URL, project_id, branch), ignore_errors=True)
