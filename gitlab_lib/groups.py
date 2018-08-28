#
# Central lib for Gitlab Tools - Group code
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


#
# SUBROUTINES
#

def create_group(groupname=None, owner=None, comment=None, end_date=None, visibility_level="private"):
    """
    Create a new group with given owner
    Return group details as json
    """

    description = ""

    if comment:
        description = comment

    if end_date:
        description += " expires " + end_date

    group = post(CREATE_GROUP % (API_BASE_URL,), {"name": groupname,
                                             "path": groupname,
                                             "description": description,
                                             "visibility_level": visibility_level,
                                             "lfs_enabled": 1})

    if group and owner:
        user = fetch(USER_BY_USERNAME % (API_BASE_URL, owner))[0]

        if user:
            add_group_member(group["id"], user["id"], permissions.ACCESS_LEVEL_OWNER)

    return group


def delete_group(group):
    """
    Deletes the group with the given name or id
    """

    if not type(group) == dict:
        group = get_group(group)

    if group:
        return delete(DELETE_GROUP % (API_BASE_URL, group["id"]))


def add_group_member(group, user, access_level=permissions.ACCESS_LEVEL_GUEST):
    """
    Add a new member to the given group
    Group and user parameter can be either name or id
    Access level is optional
    """

    group_id = convert_group_to_id(group)
    return post(ADD_GROUP_MEMBER % (API_BASE_URL, group_id), {"id": group_id,
                                                         "user_id": convert_group_to_id(user),
                                                         "access_level": access_level})


def get_group(group=None):
    """
    Get metadata of a single group
    Parameter group can be name or id
    """

    try:
        int(group)
        return fetch(GROUP_BY_ID % (API_BASE_URL, group))
    except (TypeError, ValueError):
        result = fetch(GROUP_BY_GROUPNAME % (API_BASE_URL, group))

        if result:
            return result[0]
        else:
            return None


def get_group_projects(group):
    """
    Get projects of group
    Group can be either name or id
    """

    return fetch(GROUP_PROJECTS % (API_BASE_URL, convert_group_to_id(group)))


def get_group_members(group):
    """
    Get members of group
    Group can be either name or id
    """

    return fetch(GROUP_MEMBERS % (API_BASE_URL, convert_group_to_id(group)))


def convert_group_to_id(group):
    """
    Try to use group as id (int)
    Otherwise fetch group by name
    """
    try:
        group_id = int(group)
    except (TypeError, ValueError):
        group_id = fetch(GROUP_BY_GROUPNAME % (API_BASE_URL, group))[0].get("id")

    return group_id
