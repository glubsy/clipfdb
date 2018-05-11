#!/bin/python3

import os
import sys
import re
import fdb_embedded as fdb

# Use database, or use actual dir?


# 1: fetch all _1280 files from CGI.db, build list in file
# path/file_1280.ext
# 2: for each file_, lookup in download.db
# if _raw is found, should be moved
# if no _raw is found, should be listed in separate list for further investigation
#
# path/file_1280.ext path/file_raw.ext

# make list of 1280
# exclude those to delete (list from tumbler_scrape.txt)
# -> list TODELETE (move them before delete)
# make list of 1280 with no corresponding _raw -> list REVERSE_SEARCH (move them)


repattern_tumblr_1280 = re.compile(r'tumblr_.*_1280.*', re.I)


class FDBEMBEDDED():
    """handles queries to the fdb databases"""

