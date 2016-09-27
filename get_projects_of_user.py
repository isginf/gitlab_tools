#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Show a list of personal or all projects of a specified user
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


import sys
import argparse
import gitlab_lib
import backup_config

parser = argparse.ArgumentParser()
parser.add_argument("-a", "--all", help="Show all not projects not only personal", action="store_true")
parser.add_argument("-s", "--server", help="Gitlab server name", default=backup_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=backup_config.TOKEN)
parser.add_argument("-U", "--user", help="Username to backup")
args = parser.parse_args()

if not args.server or not args.token:
    print("You must at least specify --server and --token")
    sys.exit(1)

for project in gitlab_lib.get_projects(args.user, personal=(not args.all)):
    print project['name']
