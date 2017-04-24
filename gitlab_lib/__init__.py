#
# Central lib for Gitlab Tools
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

import pwd
import grp
import os

import sys
sys.path.append("..")

#__all__ = ["groups", "projects", "permissions", "users"]
#from . import *

from .core import *
from .groups import *
from .projects import *
from .permissions import *
from .users import *


#
# Privilege separation
#

if os.geteuid() == 0:
    os.seteuid( pwd.getpwnam("git").pw_uid )
