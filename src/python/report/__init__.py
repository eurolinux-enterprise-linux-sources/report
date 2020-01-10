"""
    The main entry point to the Report library.
    Copyright (C) 2009 Red Hat, Inc

    Author(s): Gavin Romig-Koch <gavin@redhat.com>
               Adam Stokes <ajs@redhat.com>

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

import sys
import os
import os.path
import glob
import imputil
import tempfile
import tarfile
import exceptions
import re
import ConfigParser

import xml.etree.ElementTree as etree

from optparse import OptionParser
from report import io as iomodule
from report.io import DisplayFailMessage
from report.io import DisplaySuccessMessage

from report import release_information

import gettext
gettext_dir = "/usr/share/locale"
gettext_app = "report"
gettext.bindtextdomain(gettext_app, gettext_dir)

def _report(msg):
    return gettext.dgettext(gettext_app, msg)

_ = lambda x: _report(x)

#
#  A Signature, for the purposes of this library, is a mapping of names
#  to values (in Python terms a Dictionary).  For maximum portablility,
#  names must be ASCII alpha-numeric characters.  Values should be 
#  types that conform to the SignatureValue api below.
# 

class SignatureValue:
    # roughly an arbitrary value that can be collected, stored, and 
    # shipped over the wire.
    # 
    # a SignatureValue can be any type that conforms to this protocol
    #
    # asString() - return a string representation of the data
    # asFile() - return a file representation of the data
    # asFileName() - return the name of a file (on the local file
    #                system) that contains the data, can be a temporary
    #                file
    # 
    # isBinary - False if the data is a UTF-8 (or compatible) character stream,
    #            True if the data is not character data.
    # isFile - was this created as a file
    # fileName - the data has a system independent name
    #            this is generally _not_ where the data is actually
    #            stored. If you need access to the data use one of the
    #            asXXX() functions to get the data in the form you
    #            need it.
    #
    pass

class StringSignatureValue:
    def __init__(self, data, isBinary = False):
        self._data = data
        self._fileLocation = None

        self.isBinary = isBinary
        self.isFile = False

    def asString(self):
        return self._data

    def asFile(self):
        return file(self.asFileName())

    def asFileName(self):
        if not self._fileLocation:
            if self.isBinary:
                mymode = 'w+b'
            else:
                mymode = 'w+'
            tmp = tempfile.NamedTemporaryFile(mode=mymode,prefix="report-",
                                              delete=False)
            tmp.write(self._data)
            self._fileLocation = tmp.name
            tmp.close()
        return self._fileLocation

    def __del__(self):
        if self._fileLocation:
            os.remove(self._fileLocation)
            self._fileLocation = None

class NamedFileSignatureValue:
    def __init__(self, fileLocation, isBinary, fileName=None):

        # if the file can't be read for some reason (permissions, 
        # non-existance, etc.) better to notice that now, and 
        # throw an exception now - this will accomplish this
        file(fileLocation).read(1)

        self._fileLocation = fileLocation

        self.isBinary = isBinary
        self.isFile = True
        if fileName != None:
            self.fileName = fileName
        else:
            self.fileName = fileLocation

    def asString(self):
        return file(self._fileLocation).read()

    def asFile(self):
        return file(self._fileLocation)

    def asFileName(self):
        return self._fileLocation

class FileSignatureValue:
    def __init__(self, afile, isBinary, fileName=None):
        self._afile = afile

        self.isBinary = isBinary
        self.isFile = True
        self._fileLocation = None
        if fileName != None:
            self.fileName = fileName
        else:
            self.fileName = afile.name

    def asString(self):
        if self._fileLocation:
            return file(self._fileLocation).read()
        else:
            return self._afile.read()

    def asFile(self):
        if self._fileLocation:
            return file(self._fileLocation)
        else:
            return self._afile

    def asFileName(self):
        if not self._fileLocation:
            if self.isBinary:
                mymode = 'w+b'
            else:
                mymode = 'w+'
            tmp = tempfile.NamedTemporaryFile(mode=mymode,prefix="report-",
                                              delete=False)
            tmp.write(self._afile.read())
            self._fileLocation = tmp.name
            tmp.close()

            self._afile.close()
            self._afile = None

        return self._fileLocation

    def __del__(self):
        if self._fileLocation:
            os.remove(self._fileLocation)
            self._fileLocation = None

def addReleaseInformation(signature):
    if not signature:
        signature = {}

    if 'product' not in signature:
        signature['product'] = StringSignatureValue(
            release_information.getProduct())

    if 'version' not in signature:
        signature['version'] = StringSignatureValue(
            release_information.getVersion())

    return signature

def createAlertSignature(component, hashmarkername, hashvalue, summary, alertSignature):
    return addReleaseInformation(
           { "component" : StringSignatureValue(component),
             "hashmarkername" : StringSignatureValue(hashmarkername),
             "localhash" : StringSignatureValue(hashvalue),
             "summary" : StringSignatureValue(summary),
             "description" : StringSignatureValue(alertSignature) }
           )

def createPythonUnhandledExceptionSignature(component, hashmarkername, hashvalue, summary, description, exnFileName):
    return addReleaseInformation(
           { "component" : StringSignatureValue(component),
             "hashmarkername" : StringSignatureValue(hashmarkername),
             "localhash" : StringSignatureValue(hashvalue),
             "summary" : StringSignatureValue(summary),
             "description" : StringSignatureValue(description),
             "pythonUnhandledException" : NamedFileSignatureValue(exnFileName,False) }
           )

def createSimpleFileSignature(exnFileName, isBinary=True):
    return addReleaseInformation(
        { "simpleFile" : NamedFileSignatureValue(exnFileName, isBinary) }
        )

def open_signature_file( filename, io, skipErrorMessage = False ):
    try:
        tar_file = None
        if tarfile.is_tarfile( filename ):
            tar_file = tarfile.open(filename, mode='r:*')
            try:
                xml_file = tar_file.extractfile("content.xml")
            except KeyError:
                if not skipErrorMessage:
                    DisplayFailMessage(io, (_("Signature File Format Error"),
                                              _("file %s is a tarfile that does not contain a member " \
                                                "named 'context.xml'" % (filename,))))
                return False

        else:
            xml_file = file(filename)

    except Exception,e:
        if not skipErrorMessage:
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("Failed to open file %(filename)s: %(error)s" %
                                 {'filename':filename, 'error':e}))
        return False


    if not xml_file:
        if not skipErrorMessage:
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("Failed to open file %s" % (filename,)))
        return xml_file

    try:
        signature_tree = etree.parse( xml_file )

    except Exception,e:
        if not skipErrorMessage:
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("Error while parseing: %(filename)s: %(error)s" %
                                 {'filename':filename, 'error':e}))
        return False

    if not signature_tree:
        if not skipErrorMessage:
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("Could not parse XML file %s" % (filename,)))
        return signature_tree

    signature_root = signature_tree.getroot()
    if signature_root.tag != "report" and not re.match(r"\{.*\}report", signature_root.tag):
        if not skipErrorMessage:
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("file %(filename)s has document tag that is " \
                                 "not valid: %(signature)s" %
                                 {'filename':filename,'signature':signature_root.tag}))
        return False

    return (signature_root, tar_file)
        
def isSignatureFile( filename ):
    file_pair = open_signature_file( filename, None, skipErrorMessage = True )
    if not file_pair:
        return file_pair
    else:
        return True

def createSignatureFromFile( filename, io ):

    file_pair = open_signature_file( filename, io )
    if not file_pair:
        return file_pair
    
    (signature_root, tar_file) = file_pair

    signature = {}

    for each in signature_root:
        if each.tag != "binding" and not re.match(r"\{.*\}binding", each.tag):
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("file %(filename)s has document element that " \
                                 "has children with an invalid tag: %(tag)s" %
                                 {'filename':filename,'tag':each.tag}))
            return True

        if "name" in each.attrib:
            name = each.attrib["name"]
        else:
            DisplayFailMessage(io, _("Signature File Format Error"),
                               _("file %s has binding element that has no 'name' attribute" % (filename,)))
            return False

        isBinary = False
        if "type" in each.attrib:
            if each.attrib["type"] == "binary":
                isBinary = True

        fileName = None
        if "fileName" in each.attrib:
            if each.attrib["fileName"] != "":
                fileName = each.attrib["fileName"]

        if "href" in each.attrib:
            if not tar_file:
                DisplayFailMessage(io, _("Signature File Format Error"),
                                   _("file %s has a binding with an 'href' but no content" % (filename,)))
                return False

            try:
                member_name = each.attrib['href']
                afile = tar_file.extractfile(member_name)
            except KeyError:
                DisplayFailMessage(io, _("Signature File Format Error"),
                                   _("file %(filename)s is a tarfile that does not contain a " \
                                     "member named '%(member)s'" %
                                     {'filename':filename,'member':member_name}))
                return False

            if not afile:
                DisplayFailMessage(io, _("Signature File Format Error"),
                                   _("file %(filename)s is a tarfile that does not contain a " \
                                     "member named '%(member)s'" %
                                     {'filename':filename,'member':member_name}))
                return False


            signature[name] = FileSignatureValue(afile, isBinary, fileName)

        else:
            if "value" in each.attrib:
                if each.text:
                    DisplayFailMessage(io, _("Signature File Format Error"),
                                       _("file %(filename)s has a binding, %(binding)s, " \
                                         "that has both a 'value' attribute, and a text child" %
                                         {'filename':filename,'binding':name}))
                    return False
                else:
                    value = each.attrib["value"]
            else:
                if each.text:
                    value = each.text
                else:
                    DisplayFailMessage(io, _("Signature File Format Error"),
                                       _("file %(filename)s has a binding, %(binding)s, " \
                                         "that has neither a 'value' attribute, or a text child" %
                                         {'filename':filename,'binding':name}))
                    return False

            signature[name] = StringSignatureValue(value, isBinary)

    return signature


def buildChoices(signature, io, config, rptopts):
    """ builds an array of choices """
    choices = []
    choice = None

    (modulefile, modulepath, moduletype) = imputil.imp.find_module("plugins",sys.modules[__name__].__path__)
    try:
        alternatives = imputil.imp.load_module("report.plugins", modulefile, modulepath, moduletype)
    finally:
        if modulefile:
            modulefile.close()

    config_sections = config.sections()
    if "main" in config_sections:
        config_sections.remove("main")
        
    for eachSection in config_sections:
        optionsDict = {}
        for eachOption in config.options(eachSection):
            optionsDict[eachOption] = config.get(eachSection,eachOption)
        if "plugin" in optionsDict:
            moduleName = optionsDict["plugin"]
        (modulefile, modulepath, moduletype) = imputil.imp.find_module(moduleName,alternatives.__path__)
        try:
            module = imputil.imp.load_module("report.plugins." + moduleName, modulefile, modulepath, moduletype)
        finally:
            if modulefile:
                modulefile.close()
                
        for k,v in rptopts.iteritems():
            optionsDict[k] = v

        if 'target' not in optionsDict:
            choices.append( \
                iomodule.ChoiceValue( \
                    module.labelFunction(eachSection),
                    module.descriptionFunction(optionsDict),
                    (lambda module, optionsDict: lambda signature, io : module.report(signature, io, optionsDict))(module, optionsDict)))
        elif optionsDict['target'] == module.labelFunction(eachSection) :
            return (lambda module, optionsDict: lambda signature, io : module.report(signature, io, optionsDict))(module, optionsDict)


    # if we haven't loaded any choices from the config files, 
    #   assume they are not readable, load all plugins as choices
    if len(choices) == 0:

        # from the 'alternatives' directory, get the list of unique (set)
        # basenames with the extension stripped off 
        moduleNames = set(map(
                lambda x: os.path.splitext(os.path.basename(x))[0],
                glob.glob(os.path.join(alternatives.__path__[0],"*"))))

        for moduleName in moduleNames:
            if moduleName == "__init__":
                continue

            (modulefile, modulepath, moduletype) = \
                imputil.imp.find_module(moduleName,alternatives.__path__)
            try:
                module = imputil.imp.load_module(
                    "report.plugins." + moduleName, modulefile, 
                    modulepath, moduletype)
            finally:
                if modulefile:
                    modulefile.close()

            optionsDict = { 'plugin' : moduleName }
            for k,v in rptopts.iteritems():
                optionsDict[k] = v

            if 'target' not in optionsDict:
                choices.append( \
                    iomodule.ChoiceValue( \
                        moduleName,
                        module.descriptionFunction(optionsDict),
                        (lambda module, optionsDict: lambda signature, io : module.report(signature, io, optionsDict))(module, optionsDict)))

            elif optionsDict['target'] == moduleName:
                return (lambda module, optionsDict: lambda signature, io : module.report(signature, io, optionsDict))(module, optionsDict)


    if 'target' in rptopts:
        DisplayFailMessage(io, _("No Such Plugin"),
                           _("No plugin matching the requested: %s.") % rptopts['target'])
        return False

    if len(choices) >= 1:
        choice = io.queryChoice(_("Where do you want to send this report:"), choices)
        return choice

    else:
        DisplayFailMessage(io, _("No Plugins"),
                           _("No usable plugins."))
        return False

def report(signature, io, **rptopts):
    if not io:
        DisplayFailMessage(None, _("No IO specified."),
                           _("Cannot determine IO."))
        return False

    config = ConfigParser.RawConfigParser()
    config.optionxform = str

    # Just continue, if we can't read the config files
    try:
        config.read("/etc/report.conf")
        config.read(glob.glob("/etc/report.d/*.conf"))
    except:
        pass
 
    retval = False
    while (retval == False):
        choice = buildChoices(signature, io, config, rptopts)
        if not choice:
            return choice
        else:
            retval = choice(signature, io)
            if retval == False and 'target' in rptopts:
                del rptopts['target']

    return retval
# 
# This writes out the report/signature to an on-disk/over-the-wire format
#   called the 'external format'.
#
#   The external format is either an XML file, or a TAR file containing
#   an XML file, and files containing the contents of some of the members
#   of the report/signature.  A reader of the external format must 
#   be capable of reading either format, a writer of the external format
#   may choose either format, but should choose the format that is most
#   efficient for the nature of the members of the report/signature it
#   is writing.
#
#   if asSignature 
#      only non-binary members are included in the external format
#      all non-binary members are included directly into a single XML
#         file called <reportName>.xml 
# 
#   otherwise
#      all members are included in the external format
#        if there are any files in the external format
#          the external format is a tarfile called <reportName>.tar.gz 
#             which includes a member named "content".xml which is an XML
#             file containing 
#                the direct contents of all the non-file members
#                and references to all of file references
#                  the contents of all file members are stored directly
#                  in a sub-directory of the tarfile, called "contents"
#        else
#          all members are included directly into a single XML
#             file called <reportName>.xml 
#

def serialize( signature, fileNameBase, asSignature ):

    reportFile = None
    reportFileName = None

    if fileNameBase is None:
        fileNameBase = "report"
    else:
        fileNameBase = os.path.basename( fileNameBase )

    if fileNameBase == "":
        fileNameBase = "report"

    root = etree.Element("report")

    root.attrib["xmlns"] = "http://www.redhat.com/gss/strata"

    for (key,value) in signature.iteritems():
        
        if not asSignature or not value.isBinary:
            elem = etree.Element("binding", name=key)

            if value.isFile:
                if value.fileName and value.fileName != "":
                    elem.attrib["fileName"] = value.fileName

                if value.isBinary:
                    elem.attrib["type"] = "binary"
                else:
                    elem.attrib["type"] = "text"

            if asSignature or not value.isFile:
                elem.text = value.asString()

            else:
                if reportFile == None:
                    baseFile = tempfile.NamedTemporaryFile(
                        prefix=fileNameBase,
                        suffix=".tar.gz",
                        delete=False)
                    reportFileName = baseFile.name
                    reportFile = tarfile.open(mode="w|gz",
                                              fileobj=baseFile)
                        
                realfilename = value.asFileName()

                # as we copy the file into the tarball, we want to 
                # rename it slightly: remove any leading "../"'s 
                # add a leading "content" 
                # and normalize
                if value.isFile and value.fileName:
                    internalfilename = value.fileName
                else:
                    internalfilename = realfilename
                while internalfilename.startswith("../"):
                    internalfilename = internalfilename[3:]
                internalfilename = os.path.normpath("content/" + internalfilename)
                reportFile.add(realfilename, internalfilename)
                elem.attrib["href"] = internalfilename

            root.append( elem )

    rootstring = etree.tostring(root)
    if reportFile == None:
        reportFile = tempfile.NamedTemporaryFile(
            prefix=fileNameBase,
            suffix=".xml",
            delete=False)
        reportFileName = reportFile.name
        reportFile.write(rootstring)
        reportFile.close()
    else:
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        tmpfile.write(rootstring)
        tmpfile.close()
        reportFile.add(tmpfile.name,"content.xml")
        reportFile.close()
        baseFile.close()

    return reportFileName

def serializeAsSignature( signature, fileNameBase="signature" ):
    return serialize( signature, fileNameBase, asSignature=True )

def serializeAsReport( signature, fileNameBase="report" ):
    return serialize( signature, fileNameBase, asSignature=False )

#
# serializeToFile 
#   is for use by plugins that can/must only write a signature as 
#   a single file.  For 'simpleFile' reports/signatures, it serializes
#   to that file.  For 'pythonUnhandledException', 'description', and
#   'signature' reports/signatures, this serializes them as a Signature.
#   For all other repors/signatures this serializes them as a Report.
#

def serializeToFile( signature, io, fileNameBase = None ):
    if signature.has_key("simpleFile"):
        return signature["simpleFile"].asFileName()

    elif signature.has_key("pythonUnhandledException"):
        if fileNameBase is None:
            if signature["pythonUnhandledException"].isFile and \
                    signature["pythonUnhandledException"].fileName:
                fileNameBase = signature["pythonUnhandledException"].fileName
            else:
                fileNameBase = "pythonUnhandledException"
        return serializeAsSignature(signature, fileNameBase)

    elif signature.has_key("description"):
        if fileNameBase is None:
            if signature["description"].isFile and \
                    signature["description"].fileName:
                fileNameBase = signature["description"].fileName
            else:
                fileNameBase = "description"
        return serializeAsSignature(signature, fileNameBase)

    elif signature.has_key("signature"):
        if fileNameBase is None:
            if signature["signature"].isFile and \
                    signature["signature"].fileName:
                fileNameBase = signature["signature"].fileName
            else:
                fileNameBase = "signature"
        return serializeAsSignature(signature, fileNameBase)

    else:
        if fileNameBase is None:
            fileNameBase = "report"
        return serializeAsReport(signature, fileNameBase)

