import syslog
import ConfigParser

_Loglevel = None

def _GetLoglevel():
    global _Loglevel

    if _Loglevel == None:
        try:
            config = ConfigParser.RawConfigParser()
            config.optionxform = str
            config.read("/etc/report.conf")

            # Acceptable priorities for syslog
            prio_mappings = {'LOG_INFO': syslog.LOG_INFO,
                             'LOG_CRIT': syslog.LOG_CRIT,
                             'LOG_DEBUG' : syslog.LOG_DEBUG,
                             'LOG_WARNING': syslog.LOG_WARNING}

            _Loglevel = prio_mappings[config.get("main","loglevel")]
            
        except:
            _Loglevel = syslog.LOG_INFO
    return _Loglevel

def DisplayFailMessage(io, title, msg):
    """ display error message, title and msg or strings
    return nothing
    """
    logmsg = 'report: '
    if msg:
        if title:
            logmsg += title + ': ' + msg
        else:
            logmsg += msg
    else:
        if title:
            logmsg += title + ': DisplayFailMessage called without message'
        else:
            logmsg += 'DisplayFailMessage called without message'

    syslog.syslog(_GetLoglevel(), logmsg)
    if io:
        io.failMessage(title, msg)

def DisplaySuccessMessage(io, title, msg, actualURL, displayURL):
    """ display a sucess message, all args are strings,
    displayURL and actualURL should both refer to the same 
    internet resource, displayURL is for display to the user, 
    actualURL is for if you want to link to the resource.
    If actualURL is empty but displayURL is not, displayURL
    is shown but not as a link.
    if displayURL is empty but actualURL is not, displayURL
    defaults to actualURL
    displayURL and actualURL can be the same string.
    return nothing
    """
    if displayURL:
        URL = displayURL
    else:
        URL = actualURL

    logmsg = 'report: '
    if msg:
        if title:
            logmsg += title + ': ' + msg
        else:
            logmsg += msg
    else:
        if title:
            logmsg += title + ': DisplaySuccessMessage called without message'
        else:
            logmsg += 'DisplaySuccessMessage called without message'

    if URL:
        logmsg += '\n' + URL

    syslog.syslog(_GetLoglevel(), logmsg)
    if io:
        io.successMessage(title, msg, actualURL, displayURL)

class ChoiceValue:
    def __init__(self,title,explanation,returnValue):
        self.title = title
        self.explanation = explanation
        self.returnValue = returnValue

class IO:
    # IO is a callback mechinism for communicating with the user
    # IO can be any type that conforms to the following protocol
    # def infoMessage(self,title,msg):
    #   display message, title and msg are strings
    #   return nothing
    # def failMessage(self,title,msg):
    #   display an error message, title and msg are strings
    #   return nothing
    # def successMessage(self,title,msg,actualURL,displayURL)
    #   display a sucess message, all args are strings,
    #     displayURL and actualURL should both refer to the same 
    #     internet resource, displayURL is for display to the user, 
    #     actualURL is for if you want to link to the resource.
    #     If actualURL is empty but displayURL is not, displayURL
    #     is shown but not as a link.
    #     if displayURL is empty but actualURL is not, displayURL
    #       defaults to actualURL
    #     displayURL and actualURL can be the same string.
    #   return nothing
    # def queryLogin(self,account):
    #   Ask the user for the username and password for logging into
    #     account (a string).
    #   return a dictionary which contains at least two members with
    #     the keys "username" and "password".  The values of these members
    #     should be strings.
    # def updateLogin(self,account,loginResult):
    #   Update the login information for account.
    #   If you call queryLogin, and the login is then successfull,
    #     call this function with the result of the queryLogin to
    #     tell the account manager that the login was successfull
    #   returns nothing
    # def queryField(self,fieldName)
    #     asks for a string value, returns string value
    # def queryChoice(self,msg,choices):
    #    msg is a message about the choices
    #    choices is a sequence of ChoiceValues
    #      Each ChoiceValue (title,explanation,returnValue)
    #    returns the returnValue of the choice the user made
    pass



