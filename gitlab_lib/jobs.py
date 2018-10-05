#
# Central lib for Gitlab Tools - Job code
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
from .projects import get_project

#
# SUBROUTINES
#

def get_jobs(project, filter_func=None):
    """
    Get all jobs for specified project.
    Project can be project id or dict
    filter_func can be used to filter the result
    """
    chunk_size=100

    if not type(project) == dict:
        project = get_project(project)

    api_url = GET_PROJECT_JOBS % (API_BASE_URL, project["id"])

    for job in fetch_per_page(api_url, chunk_size, filter_func):
        yield project


def delete_job(project_id, job_id):
    """
    Delete the projects job with the given job_id.
    Project_id and job_id must be integer
    """
    api_url = DELETE_PROJECT_JOB % (API_BASE_URL, project_id, job_id)

    return post(api_url)
