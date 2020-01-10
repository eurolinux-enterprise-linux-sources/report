# Copyright (C) 2008, 2009, 2010  Red Hat, Inc.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author(s): Gavin Romig-Koch <gavin@redhat.com>
#

import os

SYSTEM_RELEASE_PATHS = ["/etc/system-release","/etc/redhat-release"]
SYSTEM_RELEASE_DEPS = ["system-release", "redhat-release"]

_hardcoded_default_product = ""
_hardcoded_default_version = ""

def getProduct_fromRPM():
    try:
        import rpm
        ts = rpm.TransactionSet()
        for each_dep in SYSTEM_RELEASE_DEPS:
            mi = ts.dbMatch('provides', each_dep)
            for h in mi:
                if h['name']:
                    return h['name'].split("-")[0].capitalize()

        return ""
    except:
        return ""

def getProduct_fromPRODUCT():
    try:
        import product
        return product.productName
    except:
        return ""

def getVersion_fromRPM():
    try:
        import rpm
        ts = rpm.TransactionSet()
        for each_dep in SYSTEM_RELEASE_DEPS:
            mi = ts.dbMatch('provides', each_dep)
            for h in mi:
                if h['version']:
                    return str(h['version'])

        return ""
    except:
        return ""

def getVersion_fromFILE():
    for each_path in SYSTEM_RELEASE_PATHS:
        if os.path.exists(each_path):
            file = open(each_path, "r")
            content = file.read()
            if content.find("Rawhide") > -1:
                return "rawhide"
        
            clist = content.split(" ")
            i = clist.index("release")
            return clist[i+1]
        else:
            return ""

def getVersion_fromPRODUCT():
    try:
        import product
        return product.productVersion
    except:
        return ""


def getProduct():
    """Attempt to determine the product of the running system by first asking
       rpm, and then falling back on a hardcoded default.
    """
    product = getProduct_fromRPM()
    if product:
        return product
    product = getProduct_fromPRODUCT()
    if product:
        return product

    return _hardcoded_default_product

def getVersion():
    """Attempt to determine the version of the running system by first asking
       rpm, and then falling back on a hardcoded default.  Always return as
       a string.
    """
    version = getVersion_fromRPM()
    if version:
        return version
    version = getVersion_fromFILE()
    if version:
        return version
    version = getVersion_fromPRODUCT()
    if version:
        return version

    return _hardcoded_default_version

