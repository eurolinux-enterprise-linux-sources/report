"""
    A Report plugin to send a report to the Strata API.
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
import re

from report import io as iomodule
from report.io import DisplaySuccessMessage
from report.io import DisplayFailMessage
import report as reportmodule
from report import _report as _
import xml.etree.ElementTree as etree

import report.release_information

from .strata import post_signature, send_report_to_new_case, send_report_to_existing_case, strata_client_strerror

def labelFunction(label):
    if label:
        return label
    return 'strata'

def descriptionFunction(optionsDict):
    if optionsDict.has_key('description'):
        return optionsDict['description']
    return 'strata plugin'

def strataURL(optionsDict):
    if optionsDict.has_key("strataURL"):
        return optionsDict["strataURL"]
    strata_host = "access.redhat.com"
    if optionsDict.has_key("strata_host"):
        strata_host = optionsDict["strata_host"]
    return "http://" + strata_host + "/Strata"



def report(signature, io, optionsDict):

    if not io:
        DisplayFailMessage(None, _("No IO"),
                           _("No io provided."))
        return False
    
    fileName = reportmodule.serializeAsReport(signature)

    if fileName is None:
        return None

    elif fileName is False:
        return False

    if 'component' in signature:
        component = signature['component'].asString()
    else:
        component = None

    if 'summary' in signature:
        summary = signature['summary'].asString()
    else:
        summary = None

    if not summary:
        if not component:
            summary = "Case Created By Report Library"
        else:
            summary = "Case Created for %s" % (component,)

    if 'description' in signature:
        description = signature['description'].asString()
    else:
        description = None

    if not description:
        description = summary

    rpt = fileName

    choice_attach = 4
    choice_new = 5
    if 'ticket' in optionsDict:
        choice = choice_attach

    else:
        choices = [
            iomodule.ChoiceValue(_("Create Case"), _("Create a Case"), choice_new),
            iomodule.ChoiceValue(_("Attach to existing case"), _("Attach to existing case"), choice_attach)
            ]

        choice = io.queryChoice(_("Create new case or Attach report to existing case?"), choices)
        if choice is None:
            return None


    URL = strataURL(optionsDict)

    strata_host = os.path.basename(os.path.dirname(URL))
    loginResult = io.queryLogin(strata_host)
    if not loginResult:
        return None
    
    if 'username' not in loginResult and \
            'password' not in loginResult:
        DisplayFailMessage(io, _("Missing Login Information"),
                           _("Please provide a valid username and password."))
        return False
    

    if choice == choice_new:
        if 'product' in signature:
            product = signature['product'].asString()
        else:
            product = report.release_information.getProduct()

        if 'version' in signature:
            version = signature['version'].asString()
        else:
            version = report.release_information.getVersion()

        response = send_report_to_new_case(URL, 
                                           loginResult['username'], 
                                           loginResult['password'], 
                                           summary, description, 
                                           component, 
                                           product,
                                           version,
                                           rpt)
        if not response:
            DisplayFailMessage(io, _("Case Creation Failed"), strata_client_strerror())
            return False

        title = _("Case Creation Response")
        body = _("Case Creation Succeeded")
        displayURL = ""
        actualURL = ""

    elif choice == choice_attach:
        if 'ticket' in optionsDict:
            case_number = optionsDict['ticket']
        else:
            case_number = io.queryField("Enter existing case number")

            if case_number is None:
                return None

        response = send_report_to_existing_case(URL, 
                                                loginResult['username'], 
                                                loginResult['password'],
                                                case_number, rpt)
        
        if not response:
            DisplayFailMessage(io, _("Report Attachement Failed"), strata_client_strerror())
            return False

        title = _("Report Attachment Response")
        body = _("Report Attachment Succeded")
        displayURL = ""
        actualURL = ""

    io.updateLogin(strata_host, loginResult)

    try:
        xml = etree.XML(response)
    except Exception,e:
        xml = None

    if xml:
        for each in xml:
            if each.tag == "title" and each.text:
                title = each.text
            elif each.tag == "body" and each.text:
                body = each.text
            elif each.tag == "URL":
                if each.text:
                    displayURL = each.text
                if 'href' in each.attrib and each.attrib['href']:
                    actualURL = each.attrib['href']
    else:
        body = response

    if 'buttonURLPattern' in optionsDict:
        buttonURLPattern = optionsDict['buttonURLPattern']
    else:
        buttonURLPattern = None

    if 'buttonURLRepl' in optionsDict:
        buttonURLRepl = optionsDict['buttonURLRepl']
    else:
        buttonURLRepl = None

    if buttonURLPattern and buttonURLRepl:
        if actualURL:
            newURL = re.sub(buttonURLPattern, 
                            buttonURLRepl, 
                            actualURL)
            if displayURL == actualURL:
                displayURL = newURL
            actualURL = newURL

    DisplaySuccessMessage(io, title, body, actualURL, displayURL)
    return True

