#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Search for a Gitlab project using the REST API
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
# LOADING MODULES
#

import sys
import argparse
import gitlab_lib
import backup_config


#
# PARAMETERS
#
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--details", help="Print all project properties", action="store_true")
parser.add_argument("-p", "--project", help="Project name or id in Gitlab")
parser.add_argument("-s", "--server", help="Gitlab server name", default=backup_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=backup_config.TOKEN)
args = parser.parse_args()

if not args.server or not args.token or not args.project:
    print "You must at least specify --server, --token and --project"
    sys.exit(1)


#
# MAIN PART
#
projects = []

try:
    projects.append(gitlab_lib.fetch(gitlab_lib.PROJECT_METADATA % (int(args.project),)))
except ValueError:
    projects = [x for x in gitlab_lib.get_projects() \
                if args.project in (x['name_with_namespace'] or x['description'])]

if len(projects) == 0:
    print "Found nothing"
else:
    for project in projects:
        if args.details:
            keys = project.keys()
            keys.sort()

            for key in keys:
                print u"%s: %s" % (key, project[key])
                print u"-" * 79

            print "\n"
        else:
            print "%d %s" %(project['id'], project['name_with_namespace'])
