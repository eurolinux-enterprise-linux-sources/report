"""
    A console/text plugin for the general purpose I/O functions provided to
       report plugins.
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

import getpass

class TextIO:
    def infoMessage(self,title,msg):
        print 
        print title
        print msg

    def failMessage(self,title,msg):
        print 
        print title
        print msg

    def successMessage(self, title, msg, actualURL, displayURL):
        print 
        print title
        print msg
        if displayURL:
            print displayURL
        if actualURL and actualURL != displayURL:
            print actualURL

    def queryLogin(self, accountName):
        print
        print "Login for %s" % accountName
        try:
            username = raw_input("Username: ")
            password = getpass.getpass("Password: ")
        except EOFError:
            print "input canceled (EOF)"
            return None

        responseDict = {}
        responseDict['username'] = username
        responseDict['password'] = password
        responseDict['remember'] = False
        return responseDict

    def updateLogin(self,accountName,loginResult):
        pass

    def queryField(self,fieldName):
        print
        try:
            fieldValue = raw_input("%s: " % fieldName)
        except EOFError:
            print "input canceled (EOF)"
            return None
        return fieldValue

    def queryChoice(self,msg,choices):
        while True:
            print("\n")
            print(msg)

            count = 1
            for each in choices:
                print "%s: %s" % (count,each.title)
                count += 1
            print "0: %s" % ("cancel",)

            try:
                choice = raw_input("Choice (0-%s): " % (count-1,))
            except EOFError:
                print "input canceled (EOF)"
                return None
            try:
                choice = int(choice)
            except ValueError:
                choice = count
            if 0 < choice and choice < count:
                return choices[choice-1].returnValue
            if choice == 0:
                return None
            print "Invalid choice"


