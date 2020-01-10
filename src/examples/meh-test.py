#!/bin/env python

import meh

class Config:
      def __init__(self):
          self.config_value_one = 1
          self.config_value_two = 2



meh.makeRHHandler("crash-test-meh", "1.0", Config())

print "handler set up, about to divide by zero"

zero = 0
print 1 / zero

print "should have crashed"




