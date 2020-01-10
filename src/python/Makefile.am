nobase_dist_pyexec_DATA = \
report/__init__.py report/accountmanager.py \
report/release_information.py \
report/plugins/__init__.py \
report/plugins/strata/__init__.py \
report/plugins/strata/strata.py \
report/plugins/bugzilla/__init__.py \
report/plugins/bugzilla/filer.py \
report/plugins/RHEL-bugzilla/__init__.py \
report/plugins/RHEL-bugzilla/filer.py \
$(wildcard report/plugins/RHEL-bugzilla/bugzillaCopy/*.py) \
report/io/__init__.py \
report/io/GTKIO.py \
report/io/TextIO.py \
report/io/NewtIO.py \
$(wildcard report/plugins/ftp/*.py) \
report/plugins/localsave/__init__.py \
report/plugins/scp/__init__.py

bin_SCRIPTS = bin/report

EXTRA_DIST = $(bin_SCRIPTS) gettext.h
dist_man_MANS = bin/report.1


nobase_dist_noinst_DATA = report/plugins/RHEL-bugzilla/bugzillaCopy/VERSION

LDADD= $(LIBINTL)

