#!/usr/bin/python

from report.io.TextIO import TextIO
from report.io.GTKIO import GTKIO
from report.io.NewtIO import NewtIO
from report.io import DisplaySuccessMessage
from report.io import DisplayFailMessage

import sys
from report import io as iomodule
from report import accountmanager

keeplooping = True

def ChoiceOneFunction(io):
    io.infoMessage("Your Choice","You choose Choice One")

def ChoiceTwoFunction(io):
    io.infoMessage("Your Choice","You choose Choice Two")

def ChoiceQuitFunction(io):
    global keeplooping
    keeplooping = False

def doit():
    global keeplooping

    if len(sys.argv) == 2 and sys.argv[1].lower() == "gtk":
        io = GTKIO(accountmanager.AccountManager())

    elif len(sys.argv) == 2 and sys.argv[1].lower() == "text":
        io = TextIO()

    elif len(sys.argv) == 2 and sys.argv[1].lower() == "newt":
        io = NewtIO()

    else:
        io = NewtIO()    

    io.infoMessage("IOTest", 
                   "This is the start of IOTest\n" + \
                   "This is also an example of an infoMessage")
                   
    DisplayFailMessage(io,
                       "IOTest", 
                       "This is an example of a failMessage\n" + \
                       "Nothing has actually failed, this is just a test.")

    bugURL = "http:/bugzilla.redhat.com/"
    bugDisplayURL = "http:/bugzilla.redhat.com/hello"
    DisplaySuccessMessage(io,
                          "IOTest",
                          "This is an example of a successMessage",
                          bugURL,
                          bugDisplayURL)


    io.infoMessage("IOTest", 
                   "about to test the input dialog, please try:\n" + \
                       "1) entering nothing\n" + \
                       "2) entering just blanks\n" + \
                       "3) something other than blanks\n" + \
                       "4) 'quit'\n" + \
                       "keeps looping till 'quit' is entered")


    keeplooping = True
    while keeplooping:
        output = io.queryField("Please enter some text")
            
        if output == None:
            io.infoMessage("Input Dialog Test", "You canceled the input")

        elif output.strip() == "":
            io.infoMessage("Input Dialog Test", "You entered nothing or just blanks")

        else:
            io.infoMessage("Input Dialog Test", "You entered '%s'" % output)
            if output == "quit":
                keeplooping = False


    io.infoMessage("IOTest", 
                   "about to test the login dialog, please try:\n" + \
                       "1) no username\n" + \
                       "2) username and password not equal\n" + \
                       "3) username and password equal\n" + \
                       "keeps looping till username == 'quit'")

    keeplooping = True
    while keeplooping:
        loginHost = "bugzilla.redhat.com"
        loginResult = io.queryLogin(loginHost)
        if loginResult == None:
            io.infoMessage("Input Dialog Test", "You canceled the input")
            
        elif not loginResult or loginResult['username'] == "":
            DisplayFailMessage(io,
                               "No Login Information",
                               "Please provide a valid username and password.")

        else:
            password = loginResult['password']
            username = loginResult['username']
            if username == password:
                io.infoMessage("Successful Login",
                               "Username and Password equal")
                io.updateLogin(loginHost,loginResult)
            else:
                DisplayFailMessage(io,
                                   "Login Failure",
                                   "Username and Password not equal")

            if username == 'quit':
                keeplooping = False

    io.infoMessage("IOTest", 
                   "about to test the choice dialog, please try:\n" + \
                       "1) Choice One\n" + \
                       "2) Choice Two\n" + \
                       "3) Not a number\n" + \
                       "4) Number outside valid range\n" + \
                       "5) Quit\n" + \
                       "keeps looping till 'Quit'")

    keeplooping = True
    while keeplooping: 
        choices = []
        choices.append(iomodule.ChoiceValue("Choice One", "This is Choice One", ChoiceOneFunction))
        choices.append(iomodule.ChoiceValue("Choice Two", "This is Choice Two", ChoiceTwoFunction))
        choices.append(iomodule.ChoiceValue("Quit", "This will leave the Choice Test Loop", ChoiceQuitFunction))

        choice = io.queryChoice("What Function do you Want to run?",
                                choices)

        if choice is None:
            DisplayFailMessage(io,
                               "None",
                               "You canceled the input")
        else:
            choice(io)

try:
    doit()
except:
    (exc_type,exc_value,exc_traceback) = sys.exc_info()
    print "Type:", exc_type
    print "Value:", exc_value
    raise

