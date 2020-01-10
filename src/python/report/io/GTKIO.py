"""
    A GTK plugin for the general purpose I/O functions provided to
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

from report import _report as _
import report.accountmanager
import os
if 'DISPLAY' in os.environ and len(os.environ["DISPLAY"]) > 0: 
    import gtk

class GTKIO:
    def __init__(self,loginManager = None):
        import gtk
        if loginManager == None:
            loginManager = report.accountmanager.AccountManager()
        self.loginManager = loginManager

    def infoMessage(self,title,msg):
        MessageDialog(title,msg)

    def failMessage(self,title,msg):
        FailDialog(title,msg)

    def successMessage(self, title, msg, actualURL, displayURL):
        SuccessDialog(title, msg, actualURL, displayURL)

    def queryLogin(self, accountName):
        (accountName,username,password,remember) = \
            self.loginManager.queryLogin(accountName)
        return LoginDialog(accountName,username,password,remember).run()

    def updateLogin(self,accountName,loginResult):
        self.loginManager.updateLogin(accountName,loginResult)

    def queryField(self,fieldName):
        return FieldDialog(fieldName).run()

    def queryChoice(self,msg,choices):
        buttons = ()
        returnValues = []
        count = 0
        for each in choices:
            count += 1
            buttons += (each.title,count)
            returnValues.append(each.returnValue)

        choice = ButtonBoxDialog(msg,buttons).run()

        if not choice or choice < 1 or count < choice:
            return None

        return returnValues[choice-1]

class LoginDialog:
    def __init__(self, account, username, password, remember):
        self.dialog =  gtk.Dialog(_("Login for %s" % account), None, 
                                  gtk.DIALOG_MODAL, 
                                  (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                   gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.dialog.set_resizable(True)  
        self.dialog.set_border_width(0)
        self.dialog.set_position(gtk.WIN_POS_CENTER)
        self.dialog.set_default_response(gtk.RESPONSE_ACCEPT)

        usernameHBox = gtk.HBox(False,10)
        self.dialog.vbox.pack_start(usernameHBox, True, True, 0)

        usernameLabel = gtk.Label(_("Username"))
        usernameHBox.pack_start(usernameLabel, True, True, 0)

        self.usernameEntry = gtk.Entry()
        self.usernameEntry.set_text(username)
        self.usernameEntry.set_visibility(True)
        self.usernameEntry.set_activates_default(True)
        usernameHBox.pack_start(self.usernameEntry, True, True, 0)

        passwordHBox = gtk.HBox(False,10)
        self.dialog.vbox.pack_start(passwordHBox, True, True, 0)

        passwordLabel = gtk.Label(_("Password"))
        passwordHBox.pack_start(passwordLabel, True, True, 0)

        self.passwordEntry = gtk.Entry()
        self.passwordEntry.set_text(password)
        self.passwordEntry.set_visibility(False)
        self.passwordEntry.set_activates_default(True)
        passwordHBox.pack_start(self.passwordEntry, True, True, 0)

        if remember == None:
            self.keyringCheckBox = None
        else:
            self.keyringCheckBox = gtk.CheckButton(
                _("Save password in keyring"))
            self.dialog.vbox.pack_start(self.keyringCheckBox, True, True, 0)
            self.keyringCheckBox.set_active(remember)

    def run(self):
        self.dialog.show_all()
        rc = self.dialog.run()
        responseDict = {}
        if rc == gtk.RESPONSE_ACCEPT:
            responseDict['username'] = self.usernameEntry.get_text()
            responseDict['password'] = self.passwordEntry.get_text()
            if self.keyringCheckBox == None:
                responseDict['remember'] = None
            else:
                responseDict['remember'] = self.keyringCheckBox.get_active()
            self.dialog.destroy()
            return responseDict
        else:
            self.dialog.destroy()
            return None


class FieldDialog:
    def __init__(self, fieldName):
        self.dialog =  gtk.Dialog(_("Enter %s") % fieldName, None, 
                                  gtk.DIALOG_MODAL, 
                                  (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                   gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.dialog.set_resizable(True)  
        self.dialog.set_border_width(0)
        self.dialog.set_position(gtk.WIN_POS_CENTER)
        self.dialog.set_default_response(gtk.RESPONSE_ACCEPT)

        fieldHBox = gtk.HBox(False,10)
        self.dialog.vbox.pack_start(fieldHBox, True, True, 0)

        fieldLabel = gtk.Label(fieldName)
        fieldHBox.pack_start(fieldLabel, True, True, 0)

        self.fieldEntry = gtk.Entry()
        self.fieldEntry.set_visibility(True)
        self.fieldEntry.set_activates_default(True)
        fieldHBox.pack_start(self.fieldEntry, True, True, 0)

    def run(self):
        self.dialog.show_all()
        rc = self.dialog.run()
        if rc == gtk.RESPONSE_ACCEPT:
            r = self.fieldEntry.get_text()
            self.dialog.destroy()
            return r
        else:
            self.dialog.destroy()
            return None

class ButtonBoxDialog:
    def __init__(self, msg, buttons):

        self.dialog =  gtk.Dialog(msg, None, gtk.DIALOG_MODAL)

        self.dialog.set_resizable(True)  
        self.dialog.set_border_width(0)
        self.dialog.set_position(gtk.WIN_POS_CENTER)

        label = gtk.Label(msg)
        self.dialog.vbox.pack_start(label)

        for i in range(0, len(buttons), 2):
            label_item = buttons[i]
            response_item = buttons[i+1]
            button = gtk.Button(label=label_item)
            button.connect("clicked", 
                           lambda b, r: self.dialog.response(r), 
                           response_item)
            self.dialog.vbox.pack_start(button)


        button = gtk.Button(stock=gtk.STOCK_CANCEL)
        button.connect("clicked", 
                       lambda b, r: self.dialog.response(r), 
                       gtk.RESPONSE_REJECT)
        self.dialog.vbox.pack_start(button) 


    def run(self):
        self.dialog.show_all()
        rc = self.dialog.run()
        self.dialog.destroy()
        return rc

class FailDialog():
    def __init__(self, title, message):
        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_ERROR,
                                gtk.BUTTONS_OK,
                                message)
        dlg.set_title(title)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()

class MessageDialog():
    def __init__(self, title, message):
        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO,
                                gtk.BUTTONS_OK,
                                message)
        dlg.set_title(title)
        dlg.set_position(gtk.WIN_POS_CENTER)
        dlg.set_default_response(message)
        dlg.set_activates_default(True)
        dlg.show_all()
        rc = dlg.run()
        dlg.destroy()

class SuccessDialog():
    def __init__(self, title, message, actualURL, displayURL):

        # a blank URL is an empty URL
        if actualURL and "" == actualURL.strip():
            actualURL = None

        if displayURL and "" == displayURL.strip():
            displayURL = None

        # default display to actual
        if actualURL and not displayURL:
            displayURL = actualURL

        dlg = gtk.MessageDialog(None, 0, gtk.MESSAGE_INFO,
                                gtk.BUTTONS_OK,
                                message)
        dlg.set_title(title)
        dlg.set_position(gtk.WIN_POS_CENTER)

        # if actual, create link
        if actualURL:
            linkbutton = gtk.LinkButton(actualURL,displayURL)
            dlg.vbox.pack_start(linkbutton, True, True, 0)
        # if just display, create label
        elif displayURL:
            label = gtk.Label(displayURL)
            dlg.vbox.pack_start(label, True, True, 0)

        dlg.show_all()
        dlg.run()
        dlg.destroy()

