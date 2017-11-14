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

from gitlab_config import SERVER

API_BASE_URL = "https://%s/api/v4" % (SERVER,)

#
# USER API
#

CREATE_USER = "%s/users"
DELETE_USER = "%s/users/%d"
GET_NO_OF_USERS = "%s/users?per_page=%d&page=%d"
USER_METADATA = "%s/users/%s"
USER_BY_USERNAME = "%s/users?username=%s"
USER_SSHKEYS = "%s/users/%s/keys"
USER_EMAILS = "%s/users/%s/emails"
BLOCK_USER = "%s/users/%s/block"
UNBLOCK_USER = "%s/users/%s/unblock"


#
# GROUP API
#

CREATE_GROUP = "%s/groups"
ADD_GROUP_MEMBER = "%s/groups/%d/members"
GROUP_MEMBERS = "%s/groups/%s/members"
GROUP_PROJECTS = "%s/groups/%d/projects"
GROUP_BY_GROUPNAME = "%s/groups?search=%s"
GROUP_BY_ID = "%s/groups/%d"


#
# PROJECTS API
#

PROJECT_COMPONENTS = {
    "request_access": "%s/projects/%s/access_requests",
    "boards": "%s/projects/%s/boards",
    "issues": "%s/projects/%s/issues",
    "labels": "%s/projects/%s/labels",
    "members": "%s/projects/%s/members",
    "milestones": "%s/projects/%s/milestones",
    "merge_requests": "%s/projects/%s/merge_requests",
    "snippets": "%s/projects/%s/snippets"
}

CREATE_PROJECT = "%s/projects"
DELETE_PROJECT = "%s/projects/%d"
PROJECT_MEMBERS = "%s/projects/%d/members"
PROJECT_METADATA = "%s/projects/%d"
PROJECT_SEARCH = "%s/projects?search=%s"
ADD_PROJECT_MEMBER = "%s/projects/%d/members"
EDIT_PROJECT_MEMBER = "%s/projects/%d/members/%d"
DEL_PROJECT_MEMBER = "%s/projects/%d/members/%d"
GET_NO_OF_PROJECTS = "%s/projects?per_page=%d&page=%d"
PROTECT_BRANCH = "%s/projects/%d/repository/branches/%s/protect"

GET_SNIPPET_CONTENT = "%s/projects/%d/snippets/%d/raw"
NOTES_FOR_SNIPPET = "%s/projects/%s/snippets/%s/notes"

NOTES_FOR_ISSUES = "%s/projects/%s/issues/%s/notes"
MERGE_REQUESTS_FOR_ISSUES = "%s/projects/%d/issues/%d/closed_by"
ISSUES_EDIT = "%s/projects/%s/issues/%s"

NOTES_FOR_MERGE_REQUESTS = "%s/projects/%s/merge_requests/%s/notes"
MERGE_REQUESTS_EDIT = "%s/projects/%s/merge_requests/%s"

GET_NAMESPACES = "%s/namespaces"
SEARCH_NAMESPACE = "%s/namespaces?search=%s"


#
# PERMISSION
#

VISIBILITY_PRIVATE=0
VISIBILITY_INTERNAL=10
VISIBILITY_PUBLIC=20
