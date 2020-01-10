"""
    A Report plugin to send a report to another host using SCP.
    Copyright (C) 2009 Red Hat, Inc

    Author(s): Gavin Romig-Koch <gavin@redhat.com>
               Adam Stokes <ajs@redhat.com>

    Much of the code in this module was derived from code written by
    Chris Lumens <clumens@redhat.com> and Will Woods <wwoods@redhat.com>.

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
import pty
from report.io import DisplaySuccessMessage
from report.io import DisplayFailMessage
from report import _report as _

import report as reportmodule

def labelFunction(label):
    if label:
        return label
    return 'scp'
def descriptionFunction(optionsDict):
    if optionsDict.has_key('description'):
        return optionsDict['description']
    return "scp the problem to a given host and filename"
    
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
        return copyFileToRemote(fileName, io, optionsDict)

def scpAuthenticate(master, childpid, password):
    childoutput = ""
    while True:
        # Read up to password prompt.  Propagate OSError exceptions, which
        # can occur for anything that causes scp to immediately die (bad
        # hostname, host down, etc.)
        buf = os.read(master, 4096)
        childoutput += buf
        if buf.lower().find("password: ") != -1:
            os.write(master, password+"\n")
            # read the space and newline that get echoed back
            buf = os.read(master, 2)
            childoutput += buf
            break

    while True:
        try:
            buf = os.read(master, 4096)
            childoutput += buf
        except (OSError, EOFError):
            break

    (pid, childstatus) = os.waitpid (childpid, 0)
    return (childstatus,childoutput)

def copyFileToRemote(exnFileName, io, optionsDict):

    if optionsDict.has_key('host'):
        host = optionsDict['host']
    else:
        host = io.queryField("host")
    if host == None:
        return None
    if not host or host.strip() == "":
        DisplayFailMessage(io, _("No Host"),
                           _("Please provide a valid hostname"))
        return False
        
    if host.find(":") != -1:
        (host, port) = host.split(":")

        # Try to convert the port to an integer just as a check to see
        # if it's a valid port number.  If not, they'll get a chance to
        # correct the information when scp fails.
        try:
            int(port)
            portArgs = ["-P", port]
        except ValueError:
            portArgs = []
    else:
        portArgs = []

    loginResult = io.queryLogin(host)
    if not loginResult:
        return None
    
    if 'username' not in loginResult and \
        'password' not in loginResult:
        DisplayFailMessage(io, _("Login Input Failed"),
                           _("Please provide a valid username and password"))
        return False

    if 'path' in optionsDict:
        path = optionsDict['path']
    else:
        path = io.queryField("path")
    if path == None:
        return None
    if not path or path.strip() == "":
        DisplayFailMessage(io, _("No Path"),
                           _("Please provide a path"))
        return False
        
    target = "%s@%s:%s" % (loginResult['username'], host, path)

    # Fork ssh into its own pty
    (childpid, master) = pty.fork()
    if childpid < 0:
        raise RuntimeError("Could not fork process to run scp")
    elif childpid == 0:
        # child process - run scp
        args = ["scp", "-oNumberOfPasswordPrompts=1",
                "-oStrictHostKeyChecking=no",
                "-oUserKnownHostsFile=/dev/null"] + portArgs + \
               [exnFileName, target]
        os.execvp("scp", args)

    # parent process
    try:
        (childstatus,childoutput) = scpAuthenticate(master, childpid, loginResult['password'])
    except OSError, e:
        DisplayFailMessage(io, _("scp failed"),
                           _("OSError during scp file from %(filename)s to %(target)s: %(error)s") %
                           {'filename':exnFileName,'target':target,'error':e})
        return False

    os.close(master)

    if os.WIFEXITED(childstatus) and os.WEXITSTATUS(childstatus) == 0:
        io.updateLogin(host,loginResult)
        DisplaySuccessMessage(io, _("scp Successful"),
                              _("The signature was successfully copied to:"),
                              None, target)
        return True
    else:
        DisplayFailMessage(io, _("scp failed"),
                           (_("unexpected child status (%(childstatus)s) during scp\n" \
                              "scp %(filename)s %(target)s\n%(childoutput)s") %
                            {'childstatus': childstatus, 'filename':exnFileName,
                             'target':target, 'childoutput':childoutput}))
        return False

