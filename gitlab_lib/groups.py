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
from . import permissions

#
# API
#

CREATE_GROUP = "%s/groups"
ADD_GROUP_MEMBER = "%s/groups/%d/members"
GROUP_MEMBERS = "%s/groups/%s/members"
GROUP_PROJECTS = "%s/groups/%d/projects"
GROUP_BY_GROUPNAME = "%s/groups?search=%s"


#
# SUBROUTINES
#

def create_group(groupname=None, owner=None, comment=None, end_date=None):
    """
    Create a new group with given owner
    Return group details as json
    """

    description = ""

    if comment:
        description = comment

    if end_date:
        description += " expires " + end_date

    group = post(CREATE_GROUP % (API_URL,), {"name": groupname,
                                             "path": groupname,
                                             "description": description,
                                             "visibility_level": 0,
                                             "lfs_enabled": 1})

    if group:
        user = fetch(USER_BY_USERNAME % (API_URL, owner))[0]

        if user:
            add_group_member(group["id"], user["id"], permissions.ACCESS_LEVEL_OWNER)

    return group


def add_group_member(group, user, access_level=permissions.ACCESS_LEVEL_GUEST):
    """
    Add a new member to the given group
    Group and user parameter can be either name or id
    Access level is optional
    """

    return post(ADD_GROUP_MEMBER % (API_URL, group_id), {"id": convert_group_to_id(group),
                                                         "user_id": convert_group_to_id(user),
                                                         "access_level": access_level})


def get_group(groupname=None):
    """
    Get metadata of a single group
    """
    result = fetch(GROUP_BY_GROUPNAME % (API_URL, groupname))

    if result:
        return result[0]
    else:
        return None


def get_group_projects(group):
    """
    Get projects of group
    Group can be either name or id
    """

    return fetch(GROUP_PROJECTS % (API_URL, convert_group_to_id(group)))


def convert_group_to_id(group):
    """
    Try to use group as id (int) 
    Otherwise fetch group by name
    """
    try:
        group_id = int(group)
    except (TypeError, ValueError):
        group_id = fetch(GROUP_BY_GROUPNAME % (API_URL, group))[0].get("id")

    return group_id
