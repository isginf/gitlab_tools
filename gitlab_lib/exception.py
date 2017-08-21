#
# Central lib for Gitlab Tools - Backup code
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

class ArchiveError(Exception):
    """Something went wrong during archivating"""
    def __init__(self, src_dir, dest_dir, message):
        self.src_dir = src_dir
        self.dest_dir = dest_dir
        self.message = message

    def __str__(self):
        return "Error archiving %s to %s: %s" % (self.src_dir, self.dest_dir, self.message)

class CloneError(Exception):
    """Something went wrong during git clone"""
    def __init__(self, repository, message):
        self.repository = repository
        self.message = message

    def __str__(self):
        return "Error cloning %s: %s" % (self.repository, self.message)

class WebError(Exception):
    """Something went wrong during web request"""
    def __init__(self, url, data={}, method="GET", message=""):
        self.url = url
        self.data = data
        self.method = method
        self.message = message

    def __str__(self):
        return "Error processing URL %s with method %s and data %s: %s" % (self.url, self.method, self.data, self.message)


class ReadError(Exception):
    """Something went wrong during reading data """
    def __init__(self, data, message):
        self.data = data
        self.message = message

    def __str__(self):
        return "Error reading %s: %s" % (self.data, self.message)


class ParseError(Exception):
    """Something went wrong during data parsing"""
    def __init__(self, data, message):
        self.data = data
        self.message = message

    def __str__(self):
        return "Error parsing %s: %s" % (self.data, self.message)
