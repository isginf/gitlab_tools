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


#
# SUBROUTINES
#

def get_namespaces(search=None):
    """
    Return a list of all namespaces
    """
    namespaces = []

    if search:
        namespaces = fetch(SEARCH_NAMESPACE % (API_BASE_URL, search))
    else:
        namespaces = fetch(GET_NAMESPACES % (API_BASE_URL,))

    return namespaces
