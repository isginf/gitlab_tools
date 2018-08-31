#!/usr/bin/python3

#
# Update permissions of all members in a project or group
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
# Import modules
#

import sys
sys.path.append("..")

import argparse
import gitlab_lib
import gitlab_config

permission = {
    "guest": gitlab_lib.ACCESS_LEVEL_GUEST,
    "reporter": gitlab_lib.ACCESS_LEVEL_REPORTER,
    "developer": gitlab_lib.ACCESS_LEVEL_DEVELOPER,
    "maintainer": gitlab_lib.ACCESS_LEVEL_MASTER,
    "owner": gitlab_lib.ACCESS_LEVEL_OWNER
}


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Show debug messages", action="store_true")
parser.add_argument("-g", "--group-name", help="Group name")
parser.add_argument("-p", "--project-name", help="Project name")
parser.add_argument("-G", "--change-group-permission", help="Change permission of group members on project", action="store_true")
parser.add_argument("-x", "--permission", help="Permission", choices=permission.keys(), required=True)
parser.add_argument("-q", "--quiet", help="No messages execpt errors", action="store_true")
parser.add_argument("-s", "--server", help="Gitlab server name", default=gitlab_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=gitlab_config.TOKEN)


args = parser.parse_args()
members = []
project = None

gitlab_lib.core.SERVER = args.server
gitlab_lib.core.TOKEN = args.token
gitlab_lib.core.DEBUG = args.debug
gitlab_lib.core.QUIET = args.quiet

if not args.server or not args.token:
    print("Need a server and token either through parameter or gitlab_config.py!")
    sys.exit(1)

if not args.group_name and not args.project_name:
    print("Need a group or project name or id")
    sys.exit(1)

if args.change_group_permission and (not args.group_name or not args.project_name):
    print("You need to specify group (-g) and project (-p) name or id to change group members permission on a project")
    sys.exit(1)


#
# SUBROUTINES
#

def access_level_to_label(int_level):
    return list(permission.keys())[list(permission.values()).index(int_level)]


#
# MAIN PART
#

if args.group_name and not args.change_group_permission:
    members = gitlab_lib.get_group_members(args.group_name)
else:
    project = gitlab_lib.get_project_metadata(args.project_name)

    if len(project) == 0:
        gitlab_lib.error("Cannot find project " + args.project_name)
        sys.exit(0)
    elif len(project) > 1:
        gitlab_lib.error("Found more than one project " + args.project_name + " specify project id")
        sys.exit(0)

    if args.change_group_permission:
        members = gitlab_lib.get_group_members(args.group_name)
    else:
        members = gitlab_lib.get_project_members(project[0]["id"])


for member in members:
    user = gitlab_lib.get_user(member["username"])

    if not user:
        gitlab_lib.error("Got member with unknown username " +  member['username'])
    else:
        gitlab_lib.info("Updating permission of member %s %s -> %s" % (user['username'], access_level_to_label(member["access_level"]), args.permission))

        if args.group_name and not args.change_group_permission:
            gitlab_lib.edit_group_member(args.group_name, user['id'], permission[args.permission])
        elif args.change_group_permission:
            gitlab_lib.add_project_member(project[0]["id"], user['id'], permission[args.permission])
        else:
            gitlab_lib.edit_project_member(project[0]["id"], user['id'], permission[args.permission])

gitlab_lib.info("Finished.")
