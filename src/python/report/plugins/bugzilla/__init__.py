"""
    A Report plugin to send a report to bugzilla.redhat.com.
    Copyright (C) 2009 Red Hat, Inc

    Author(s): Gavin Romig-Koch <gavin@redhat.com>

    Much of the code in this module is derived from code written by 
    Chris Lumens <clumens@redhat.com>.  

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
import report.io as iomodule
from report.io import DisplayFailMessage
from report.io import DisplaySuccessMessage
from report import _report as _

def labelFunction(label):
    if label:
        return label
    retValue = displayURL(optionsDict)
    if retValue.startswith("http://"):
        retValue = retValue[len("http://"):]
    if retValue.startswith("https://"):
        retValue = retValue[len("https://"):]
    return retValue

def descriptionFunction(optionsDict):
    if optionsDict.has_key("description"):
        return optionsDict["description"]
    return "Send report to " + displayURL(optionsDict)

def displayURL(optionsDict):
    if optionsDict.has_key("displayURL"):
        return optionsDict["displayURL"]
    returnURL = bugURL(optionsDict)
    if returnURL.endswith("/xmlrpc.cgi"):
        returnURL = returnURL[:len(returnURL) - len("/xmlrpc.cgi")]
    return returnURL

def bugURL(optionsDict):
    if 'bugURL' in optionsDict:
        return optionsDict["bugURL"]
    host = "bugzilla.redhat.com"
    if 'bugzilla_host' in optionsDict:
        host = optionsDict["bugzilla_host"]
    return "https://" + host + "/xmlrpc.cgi"

def report(signature, io, optionsDict):
    if not io:
        DisplayFailMessage(None, _("No IO"),
                           _("No io provided."))
        return False

    if 'pythonUnhandledException' in signature:
        fileName = signature["pythonUnhandledException"].asFileName()
        fileDescription = "Attached traceback automatically from %s." % signature["component"].asString()
    elif 'simpleFile' in signature:
        fileName = signature['simpleFile'].asFileName()
        fileDescription = "Attached file %s." % (signature['simpleFile'].asFileName(),)
    else:
        fileName = None
        fileDescription = None
    
    if 'product' in signature:
        product = signature['product'].asString()
    else:
        product = filer.getProduct()

    if 'version' in signature:
        version = signature['version'].asString()
    else:
        version = filer.getVersion()

    bzfiler = filer.BugzillaFiler(bugURL(optionsDict),
                                  displayURL(optionsDict),
                                  version, product)

    # must pass a component
    if 'component' in signature:
        component = signature["component"].asString()
    elif 'testing_component' in optionsDict:
        component = optionsDict["testing_component"]
    else:
        component = None
        
    return sendToBugzilla(component,
                          signature,
                          io,
                          bzfiler,
                          optionsDict,
                          fileName,
                          fileDescription)
                          
import filer
#
# This function was abstracted from similar code in both python-meh and
# setroubleshoot.  Beyond parameterizing this code, and using IO, this
# code differs from those others in that this version includes the
# 'component' in the .query for duplicates.
# 
def sendToBugzilla(component, signature, io, bzfiler,
                   optionsDict, fileName, fileDescription):

    import rpmUtils.arch

    class BugzillaCommunicationException (Exception):
        pass

    def withBugzillaDo(bz, fn):
        try:
            retval = fn(bz)
            return retval
        except filer.CommunicationError, e:
            msg = _("Your bug could not be filed due to the following error " \
                    "when communicating with bugzilla:\n\n%s" % str(e))
            DisplayFailMessage(io, _("Unable To File Bug"), msg)
            raise BugzillaCommunicationException()

        except (TypeError, ValueError), e:
            msg = _("Your bug could not be filed due to bad information in " \
                    "the bug fields.  This is most likely an error in " \
                    "the bug filing program:\n\n%s" % str(e))
            DisplayFailMessage(io, _("Unable To File Bug"), msg)
            raise BugzillaCommunicationException()

    try:
        if not bzfiler:
            if 'product' in signature:
                product = signature['product'].asString()
            else:
                product = filer.getProduct()

            if 'version' in signature:
                version = signature['version'].asString()
            else:
                version = filer.getVersion()

            bzfiler = filer.BugzillaFiler("https://bugzilla.redhat.com/xmlrpc.cgi",
                                          "http://bugzilla.redhat.com",
                                          version, product)

        if not bzfiler or not bzfiler.supportsFiling() or not bzfiler.bugUrl:
            DisplayFailMessage(io, _("Bug Filing Not Supported"),
                               _("Your distribution does not provide a " \
                                 "supported bug filing system, so you " \
                                 "cannot save your exception this way."))
            return False

        bugzilla_host = os.path.basename(os.path.dirname(bzfiler.bugUrl))

        loginResult = io.queryLogin(bugzilla_host)
        if not loginResult:
            return None
        
        if 'username' not in loginResult and \
            'password' not in loginResult:
            DisplayFailMessage(io, _("No Login Information"),
                               _("Please provide a valid username and password."))
            return False
    
        try:
            withBugzillaDo(bzfiler, lambda b: b.login(loginResult['username'],
                                                      loginResult['password']))
        except filer.LoginError:
            DisplayFailMessage(io, _("Unable To Login"),
                               _("There was an error logging into %s " \
                                 "using the provided username and " \
                                 "password.") % bzfiler.displayUrl)
            return False
    
        io.updateLogin(bugzilla_host, loginResult)

        # grab summary and description if we have it
        if 'summary' in signature:
            summary = signature['summary'].asString()
        else:
            summary = None

        if 'description' in signature:
            description = signature['description'].asString()
        else:
            description = None
            
        # figure out whether to attach to an existing bug, create a new bug,
        #    or search for matching bugs
        if 'ticket' in optionsDict:
            bug_number = optionsDict['ticket']
            bug = (withBugzillaDo(bzfiler, 
                                  lambda b: b.getbug(bug_number)))

            if not bug or bug == "":
                DisplayFailMessage(io, _("Bug not found"),
                                   _("Unable to find bug %s" % bug_number))
                return False
            else:
                buglist = [bug]
                wb = ""

        elif 'localhash' in signature and 'hashmarkername' in signature:
            # Are there any existing bugs with this hash value?  If so we 
            # will just add any attachment to the bug report and put the 
            # reporter on the CC list.  Otherwise, we need to create a new bug.
            wb = "%s_trace_hash:%s" % (signature['hashmarkername'].asString(), 
                                       signature['localhash'].asString())
            buglist = withBugzillaDo(bzfiler, lambda b: b.query(
                    {'status_whiteboard': wb,
                     'status_whiteboard_type':'allwordssubstr',
                     'bug_status': []}))

        elif 'component' in signature and (fileDescription or 
                                           ('description' in signature)):
            # then we should just go ahead and create a new case
            wb = ""
            buglist = []

        else:
            # ask create or attach?
            choice_attach = 4
            choice_new = 5
            choices = [
                iomodule.ChoiceValue(_("Create Case"), 
                                      _("Create a Case"), 
                                      choice_new),
                iomodule.ChoiceValue(_("Attach to existing case"), 
                                      _("Attach to existing case"), 
                                      choice_attach)
                ]

            choice = io.queryChoice(
                _("Create new case or Attach report to existing case?"), 
                choices)

            if choice is None:
                return None

            elif choice == choice_new:
                wb = ""
                buglist = []

                if 'component' not in signature:
                    component = io.queryField('Enter component for new bug');
                    if component is None:
                        return None
                    component = component.strip()

                if summary == None:
                    summary = io.queryField('Enter summary for new bug');
                    if summary == None:
                        return None
                    summary = summary.strip()

                if description == None:
                    description = io.queryField(
                        'Enter description for new bug');
                    if description is None:
                        return None
                    description = description.strip()

            else: 
                bug_number = io.queryField("Enter existing bug number")
                if bug_number == None:
                    return None

                bug = (withBugzillaDo(bzfiler, 
                                      lambda b: b.getbug(bug_number)))

                if not bug or bug == "":
                    DisplayFailMessage(io, _("Bug not found"),
                                       _("Unable to find bug %s" % bug_number))
                    return False
                else:
                    buglist = [bug]
                    wb = ""


        if not buglist or len(buglist) == 0:

            # cleanup summary and description
            if not summary or not summary.strip():
                summary = "New bug for %s" % (component,)
            
            if not description or not description.strip():
                if fileDescription:
                    description = fileDescription
                else:
                    description = ''

            bug = withBugzillaDo(bzfiler, lambda b: b.createbug(
                    product=bzfiler.getproduct(),
                    component=component,
                    version=bzfiler.getversion(),
                    platform=rpmUtils.arch.getBaseArch(),
                    bug_severity="medium",
                    priority="medium",
                    op_sys="Linux",
                    bug_file_loc="http://",
                    summary=summary,
                    comment=description,
                    status_whiteboard=wb))
    
            if fileName:
                if not fileDescription:
                    fileDescription = ""
                withBugzillaDo(bug, lambda b: b.attachfile(fileName, fileDescription,
                                     contenttype="text/plain",
                                     filename=os.path.basename(fileName)))
    
            # Tell the user we created a new bug for them and that they should
            # go add a descriptive comment.
            if bzfiler.displayUrl.endswith("/"):
                bugDisplayURL = "%s%s" % (bzfiler.displayUrl, bug.id())
            else:
                bugDisplayURL = "%s/%s" % (bzfiler.displayUrl, bug.id())
    
            bugURL = os.path.dirname(bzfiler.bugUrl) + "/show_bug.cgi?id=" + str(bug.id())

            DisplaySuccessMessage(io, _("Bug Created"),
                                  _("A new bug has been created with your traceback attached. " \
                                    "Please add additional information such as what you were doing " \
                                    "when you encountered the bug, screenshots, and whatever else " \
                                    "is appropriate to the following bug:"),
                                  bugURL,
                                  bugDisplayURL)
            return True
        else:
            bug = buglist[0]
            if fileName:
                if not fileDescription:
                    fileDescription = ""

                withBugzillaDo(bug, lambda b: b.attachfile(fileName, fileDescription,
                                    contenttype="text/plain",
                                    filename=os.path.basename(fileName)))
            withBugzillaDo(bug, lambda b: b.addCC(loginResult['username']))
    
            # Tell the user which bug they've been CC'd on and that they should
            # go add a descriptive comment.
            if bzfiler.displayUrl.endswith("/"):
                bugDisplayURL = "%s%s" % (bzfiler.displayUrl, bug.id())
            else:
                bugDisplayURL = "%s/%s" % (bzfiler.displayUrl, bug.id())
    
            bugURL = os.path.dirname(bzfiler.bugUrl) + "/show_bug.cgi?id=" + str(bug.id())

            DisplaySuccessMessage(io, _("Bug Updated"),
                                  _("A bug with your information already exists.  Your account has " \
                                    "been added to the CC list and your traceback added as a " \
                                    "comment.  Please add additional descriptive information to the " \
                                    "following bug:"),
                                  bugURL,
                                  bugDisplayURL)

            return True

    except BugzillaCommunicationException:
        # this indicates that doWithBugzilla caught some problem
        # communicating with bugzilla and displayed a message about it
        # and all we want to do now is get out of sendToBugzilla
        return False


