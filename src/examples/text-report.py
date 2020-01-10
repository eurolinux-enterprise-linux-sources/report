#!/usr/bin/python

import sys
import report
import report.io
import report.io.TextIO

if __name__ == "__main__":
    signature = report.createAlertSignature("report", 
                                            "reporttest", 
                                            "thisisafakehashvalue",
                                            "this is just a test", 
                                            "really just a test")

    rc = report.report(signature, report.io.TextIO.TextIO())

