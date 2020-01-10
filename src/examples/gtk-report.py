#!/usr/bin/python

import sys
import gtk
import report
import report.io
import report.io.GTKIO
import report.accountmanager

import sealert_test
import file_test

class MainWindow:

    def close_application(self, widget):
        gtk.main_quit()

    def do_report_fake(self, widget):
        signature = report.createAlertSignature("report", 
                                                "reporttest", 
                                                "thisisafakehashvalue",
                                                "this is just a test", 
                                                "really just a test")

        rc = report.report(signature, report.io.GTKIO.GTKIO(report.accountmanager.AccountManager()))

    def do_report_sealert(self, widget):
        signature = report.createAlertSignature(sealert_test.component, 
                                                sealert_test.hashmarkername, 
                                                sealert_test.localhash,
                                                sealert_test.summary,
                                                sealert_test.description)

        rc = report.report(signature, report.io.GTKIO.GTKIO(report.accountmanager.AccountManager()))

    def do_report_files(self, widget):
        signature = { "component" : report.StringSignatureValue(file_test.component),
                      "hashmarkername" : report.StringSignatureValue(file_test.hashmarkername),
                      "localhash" : report.StringSignatureValue(file_test.localhash),
                      "extraBinaryFile" : report.NamedFileSignatureValue(file_test.binFileName,True),
                      "helloFile" : report.NamedFileSignatureValue(file_test.textFileName,False) }


        rc = report.report(signature, report.io.GTKIO.GTKIO(report.accountmanager.AccountManager()))

    def __init__(self):

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_resizable(True)  
        self.window.connect("destroy", self.close_application)
        self.window.set_title("getfields example")
        self.window.set_border_width(0)


        box1 = gtk.VBox(False, 10)
        box1.set_border_width(10)
        self.window.add(box1)
        box1.show()

        button = gtk.Button("report-fake")
        button.connect("clicked", self.do_report_fake)
        box1.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        button = gtk.Button("report-sealert")
        button.connect("clicked", self.do_report_sealert)
        box1.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        self.window.show()

        button = gtk.Button("report-files")
        button.connect("clicked", self.do_report_files)
        box1.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        self.window.show()


def main():
    MainWindow()
    gtk.main()
    return 0

if __name__ == "__main__":
    main()

