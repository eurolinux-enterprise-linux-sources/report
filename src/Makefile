#
# Use of this file requires GNU make, or something that works
#   substantially similar to GNU make.
#
# Presuming makefile.am defines a rule for "all" (which it almost 
#   certianly does, then one can type:
#
#      make all
#
#   even if "makefile" hasn't been built from "makefile.am", and this 
#   file will cause the creation of "makefile", and then "make all"
#   will be re-run on the newly created "makefile".
#
# This file causes the creation of "makefile" if it doesn't already
#   exist.  Running "autoreconf" and "./configure" will create "makefile".
#   Once "makefile" exists, it hides this "Makefile", and make
#   will use it instead.
#
#  

GETTEXT_M4_FILE=/usr/share/aclocal/gettext.m4


include makefile

makefile: makefile.in
	./configure 

makefile.in: makefile.am
	@test -e $(GETTEXT_M4_FILE) || { echo "Error: $(GETTEXT_M4_FILE): does not exist"; echo "  autoreconf will not work without it"; echo "  On Fedora you can install it with 'yum install gettext-devel'" ; false; }
	autoreconf -i


