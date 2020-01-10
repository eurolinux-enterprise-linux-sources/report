"""
    A Report plugin to save a report to a local file.
    Copyright (C) 2009 Red Hat, Inc

    Author: Gavin Romig-Koch <gavin@redhat.com>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import os
import stat
import shutil

from report import io as iomodule
from report.io import DisplaySuccessMessage
from report.io import DisplayFailMessage
import report as reportmodule
from report import _report as _

def labelFunction(label):
    if label:
        return label
    return 'localsave'
def descriptionFunction(optionsDict):
    if optionsDict.has_key('description'):
        return optionsDict['description']
    return 'localsave plugin'

def report(signature, io, optionsDict):
    if not io:
        DisplayFailMessage(None, _("No IO"),
                           _("No io provided."))
        return False

    fileName = reportmodule.serializeToFile(signature,io)

    if fileName is None:
        return None

    elif fileName is False:
        return False

    else:
        return copyFile(fileName, io, optionsDict)

def copyFile(fileName, io, optionsDict):

    if optionsDict.has_key('path'):
        dirpath = optionsDict['path']
    else:
        dirpath = io.queryField(_("directory to store report in"))
    if dirpath == None:
        return None
    if not dirpath or dirpath.strip() == "":
        DisplayFailMessage(io, _("local save Failed"),
                           _("directory name required"))
        return False

    if os.path.exists(dirpath):
        mode = os.stat(dirpath)[stat.ST_MODE]
        if not stat.S_ISDIR(mode):
            DisplayFailMessage(io, _("local save Failed"),
                               _("'%s' already exists, but is not a directory") % dirpath)
            return False
    else:
        createp = io.queryChoice(_("'%s' does not exist, create it?") % dirpath,
                                 [ iomodule.ChoiceValue(_("OK"),
                                                        _("Create the directory"),
                                                        True),
                                   iomodule.ChoiceValue(_("Cancel"),
                                                        _("Cancel the local save"),
                                                        False) ])
        if not createp:
            return None
        
        try:
            os.makedirs(dirpath)

        except EnvironmentError, e:
            DisplayFailMessage(io, _("local save Failed"),
                               _("could not create '%(dir)s': %(error)s") % {'dir':dirpath,'error':str(e)})
            return False
            
    target = "%s/%s" % (dirpath, os.path.basename(fileName))
    try:
        if os.path.realpath(fileName) != os.path.realpath(target):
            shutil.copyfile(fileName, target)

    except EnvironmentError, e:
        DisplayFailMessage(io, _("local save Failed"),
                           _("could not save report to '%(target)s': %(error)s") % {'target':target,'error':str(e)})
        return False

    DisplaySuccessMessage(io, _("local save Successful"),
                          _("The signature was successfully copied to:"),
                          None, target)
    return True
