import site
import sys
import setuptools

site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

# Everything is defined in setup.cfg, added this file only
# to support editable mode.
setuptools.setup()
