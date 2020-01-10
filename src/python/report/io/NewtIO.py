"""
    A Newt based plugin for the general purpose I/O functions provided to
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

import snack
import gettext
_ = lambda x: gettext.ldgettext("report", x)

import string

class NewtIO:
    def __init__(self,screen = None):
        self.cleanupScreen = False
        if screen == None:
            self.screen = snack.SnackScreen()
            self.cleanupScreen = True
        else:
            self.screen = screen

    def __del__(self):
        if self.cleanupScreen:
            self.screen.finish()
            self.screen = None
            self.cleanupScreen = False

    def infoMessage(self,title,msg):
        snack.ButtonChoiceWindow(self.screen, title, msg, width=60, 
                                 buttons=[_("OK")])
        self.screen.popWindow()
        self.screen.refresh()

    def failMessage(self,title,msg):
        snack.ButtonChoiceWindow(self.screen, title, msg, width=60, 
                                 buttons=[_("OK")])
        self.screen.popWindow()
        self.screen.refresh()

    def successMessage(self, title, msg, actualURL, displayURL):

        if displayURL:
            msg += '\n    ' + displayURL
        if actualURL and actualURL != displayURL:
            msg += '\n    ' + actualURL

        snack.ButtonChoiceWindow(self.screen, title, msg, width=60, 
                                 buttons=[_("OK")])
        self.screen.popWindow()
        self.screen.refresh()

    def queryLogin(self, accountName):
        toplevel = snack.GridForm(self.screen, 
                                  _("Login for %s") % accountName,
                                  1, 2)

        buttons = snack.ButtonBar(self.screen, [_("OK"), _("Cancel")])
        usernameEntry = snack.Entry(24)
        passwordEntry = snack.Entry(24, password=1)

        grid = snack.Grid(2, 2)
        grid.setField(snack.Label(_("Username ")), 0, 0, anchorLeft=1)
        grid.setField(usernameEntry, 1, 0)
        grid.setField(snack.Label(_("Password ")), 0, 1, anchorLeft=1)
        grid.setField(passwordEntry, 1, 1)

        toplevel.add(grid, 0, 0, (0, 0, 0, 1))
        toplevel.add(buttons, 0, 1, growx=1)

        result = toplevel.run()
        rc = buttons.buttonPressed(result)

        self.screen.popWindow()
        self.screen.refresh()

        if rc == string.lower(_("OK")):
            responseDict = {}
            responseDict['username'] = usernameEntry.value()
            responseDict['password'] = passwordEntry.value()
            responseDict['remember'] = False
            return responseDict
            
        else:
            return None

    def updateLogin(self,accountName,loginResult):
        pass

    def queryField(self,fieldName):
        toplevel = snack.GridForm(self.screen, _("Enter %s") % fieldName, 1, 2)

        buttons = snack.ButtonBar(self.screen, [_("OK"), _("Cancel")])
        fieldEntry = snack.Entry(24)

        grid = snack.Grid(2, 1)
        grid.setField(snack.Label(fieldName + ' '), 0, 0, anchorLeft=1)
        grid.setField(fieldEntry, 1, 0)

        toplevel.add(grid, 0, 0, (0, 0, 0, 1))
        toplevel.add(buttons, 0, 1, growx=1)

        result = toplevel.run()
        rc = buttons.buttonPressed(result)

        self.screen.popWindow()
        self.screen.refresh()

        if rc == string.lower(_("OK")):
            return fieldEntry.value()
            
        else:
            return None

    def queryChoice(self,msg,choices):
        cancel_label = _("CANCEL")

        buttons = []
        returnValues = []
        for each in choices:
            buttons.append(each.title)
            returnValues.append(each.returnValue)

        buttons.append(cancel_label)

        toplevel = snack.GridForm(self.screen, msg, 1, 2)

        buttonBar = snack.ButtonBar(self.screen, buttons)

        toplevel.add(snack.Label(msg), 0, 0, (0, 0, 0, 1))
        toplevel.add(buttonBar, 0, 1, growx=1)

        result = toplevel.run()
        rc = buttonBar.buttonPressed(result)

        self.screen.popWindow()
        self.screen.refresh()

        if rc == cancel_label.lower():
            return None

        count = 0
        for each in buttons:
            if rc == each.lower():
                return returnValues[count]
            else:
                count += 1

        return None


