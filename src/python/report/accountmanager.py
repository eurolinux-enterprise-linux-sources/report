"""
    Utility routines for managing saved account/username/password information.
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

HAVE_gnomekeyring = False

try:
    import gnomekeyring
    HAVE_gnomekeyring = True
except:
    pass


class AccountManager:
    class LoginAccount:
        def __init__(self):
            self.username = ""
            self.remember_me = True
            self.password = None

    def __init__(self):
        self.accounts = {}

    def addAccount(self,accountName,username):
        if not self.accounts.has_key(accountName):
            self.accounts[accountName] = self.LoginAccount()

        self.accounts[accountName].username = username

    def hasAccount(self,accountName):
        return self.accounts.has_key(accountName)

    def lookupAccount(self,accountName):
        return self.accounts[accountName]

    def queryLogin(self,accountName):
        global HAVE_gnomekeyring

        if self.accounts.has_key(accountName):
            username = self.accounts[accountName].username
            password = self.accounts[accountName].password
            remember = self.accounts[accountName].remember_me

            if not username:
                username = ""
            if not password:
                password = ""
            if not remember:
                remember = False

            if not HAVE_gnomekeyring:
                remember = None

            if remember:
                try:
                    items = gnomekeyring.find_items_sync(
                        gnomekeyring.ITEM_GENERIC_SECRET, 
                        {"user": username, "server": accountName})    
                    password = items[0].secret
                except:
                    pass

        else:
            username = ""
            password = None
            remember = False

            if HAVE_gnomekeyring:
                try:
                    items = gnomekeyring.find_items_sync(
                        gnomekeyring.ITEM_GENERIC_SECRET, 
                        {"server": accountName})    
                    
                    # should not just user first, 
                    #   should use the one with the latest mtime
                    for i in range(0,len(items)):
                        if 'user' in items[i].attributes:
                            username = items[i].attributes['user']
                            password = items[i].secret
                            remember = True
                            break;

                except gnomekeyring.NoMatchError:
                    pass

                except:
                    # should log these, but for now just go on
                    pass

        if not username:
            username = ""
        if not password:
            password = ""
        if not remember:
            remember = False

        if not HAVE_gnomekeyring:
            remember = None

        return (accountName,username,password,remember)

    def updateLogin(self,accountName,loginResult):
        global HAVE_gnomekeyring

        if not loginResult.has_key('remember') or \
                loginResult['remember'] == None:
            pass

        elif loginResult['remember']:
            if not self.accounts.has_key(accountName):
                self.accounts[accountName] = self.LoginAccount()

            self.accounts[accountName].password = loginResult['password']
            self.accounts[accountName].username = loginResult['username']

            if HAVE_gnomekeyring:
                try:
                    gnomekeyring.item_create_sync(
                        gnomekeyring.get_default_keyring_sync(), 
                        gnomekeyring.ITEM_GENERIC_SECRET, 
                        "password for user %s at %s" % (
                            loginResult['username'],
                            accountName), 
                        {"user" : loginResult['username'], 
                         "server": accountName}, 
                        loginResult['password'], 
                        True)
                    
                except:
                    pass

        else:
            if self.accounts.has_key(accountName):
                del self.accounts[accountName]
        
            if HAVE_gnomekeyring:
                try:
                    items = gnomekeyring.find_items_sync(
                        gnomekeyring.ITEM_GENERIC_SECRET, 
                        {"user": loginResult['username'], 
                         "server": accountName})

                    for i in range(0,len(items)):
                        gnomekeyring.item_delete_sync(
                            items[i].keyring, 
                            items[i].item_id)

                except:
                    pass

