"""
    a report plugin to send to reports to ftp sites
    Copyright (C) 2010 Red Hat, Inc

    Author(s): Adam Stokes <ajs@redhat.com>

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
import socket

import report as reportmodule

from report.io import DisplayFailMessage
from report.io import DisplaySuccessMessage
from report import _report as _


def labelFunction(label):
    if label:
        return label
    return 'ftp'

def descriptionFunction(optionsDict):
    if optionsDict.has_key('description'):
        return optionsDict['description']
    return 'ftp plugin'

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
        return ftpFile(fileName, file(fileName), io, optionsDict)

def ftpFile(fileName, fileBlob, io, optionsDict):
    username = None
    password = None

    from urlparse import urlparse
    if optionsDict.has_key('urldir'):
        ftpserver = optionsDict['urldir']
    else:
        ftpserver = io.queryField(_("Enter remote FTP directory as URL"))

    if not ftpserver.startswith("ftp://"):
        ftpserver = "ftp://" + ftpserver

    scheme, netloc, path, params, query, fragment = urlparse(ftpserver)
    login = None
    # check for user/pass
    if netloc.find('@') > 0:
        login, netloc = netloc.split('@')
    # split user/pass
    if login and login.find(':') > 0:
        username, password = login.split(':') 
    # split netloc/port
    if netloc.find(':') > 0:
        netloc, port = netloc.split(':')
    else:
        port = 21

    try:
        import ftplib
        ftp = ftplib.FTP()
        ftp.connect(netloc, port)
        if username and password:
            ftp.login(username, password)
        else:
            ftp.login()
        ftp.cwd(path)
        ftp.set_pasv(True)
        ftp.storbinary('STOR %s' % os.path.basename(fileName), fileBlob)
        ftp.quit()
    except ftplib.all_errors, e:
        DisplayFailMessage(io, _("Upload failed"),
                           _("Upload has failed for remote path: %(ftpserver)s, %(error)s" % {'ftpserver':ftpserver,'error':e}))
        return False
    else:
        DisplaySuccessMessage(io, _("Upload Successful"),
                              _("The signature was successfully uploaded to:"),
                              None, ftpserver + '/' + os.path.basename(fileName))
        return True
