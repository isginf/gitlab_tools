#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Get one metadata of one Gitlab object like projects or groups
#
# E.g. get all members of all projects of a group 
# for PROJECT in $(./gitlab-meta-util.py -o groups -i 774 -p projects -P id); do echo -en "$PROJECT "; ./gitlab-meta-util.py -o projects -i $PROJECT -p members; done
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

import os
import sys
import argparse
import gitlab_lib
import backup_config


#
# PARAMETERS
#

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", help="Show debug messages", action="store_true")
parser.add_argument("-i", "--id", help="Object id or name")
parser.add_argument("-o", "--object", help="Gitlab object")
parser.add_argument("-p", "--property", help="Object property")
parser.add_argument("-P", "--subproperty", help="Property of object property")
parser.add_argument("-s", "--server", help="Gitlab server name", default=backup_config.SERVER)
parser.add_argument("-t", "--token", help="Private token", default=backup_config.TOKEN)
args = parser.parse_args()

if not args.server or not args.token or not args.object:
    print("You must at least specify --object, --server and --token")
    sys.exit(1)

gitlab_lib.SERVER = args.server
gitlab_lib.TOKEN = args.token
gitlab_lib.DEBUG = args.debug


#
# SUBROUTINES
#

def get_objects(obj, obj_id):
    """
    Returns a list of all gitlab objects
    Obj can be projects or users or groups etc
    """
    objects = []
    chunk_size = 100
    page = 1
    url = ""
    suffix = ""
    
    if obj == "projects":
        suffix = "/all" 

    if obj_id:
        try:
            url = "%s/%s/%d" % (gitlab_lib.API_URL, obj, int(obj_id))
        except ValueError:
            url = "%s/%s?search=%s" % (gitlab_lib.API_URL, obj, obj_id)
    else:
        url = "%s/%s%s?per_page=%d&page=%d" % (gitlab_lib.API_URL, obj, suffix, chunk_size, page)
        
    while 1:
        buff = gitlab_lib.fetch(url)

        if buff and type(buff) == list:
            objects.extend(buff)
            page += 1
        elif buff:
            objects.append(buff)

        if obj_id or not buff:
            break
        
        

    return objects


def get_property(obj, obj_id, obj_property):
    metadata = gitlab_lib.fetch("%s/%s/%d" % (gitlab_lib.API_URL, obj, obj_id))
    return metadata.get(obj_property)


def dump(obj):
    if args.property:
        prop_data = get_property(args.object, obj.get("id"), args.property)
        
        if args.subproperty:
            if type(prop_data) == list:
                for prop in prop_data:
                    print get_property(args.property, prop.get("id"), args.subproperty)
            else:
                print get_property(args.property, prop_data.get("id"), args.subproperty)
        else:            
            print prop_data
    else:
        print obj

        
#
# MAIN PART
#

for obj in get_objects(args.object, args.id):
    dump(obj)

    
    
