#!/usr/bin/python3
import os
import re
# from fdb import services

from constants import BColors
try:
    import fdb_embedded as fdb
    # from fdb_embedded import services
    FDB_AVAILABLE = True
except ImportError:
    FDB_AVAILABLE = False

class FDBquery():
    """Handles querying VVV firebird databases locally"""

    def __init__(self):
        if not FDB_AVAILABLE:
            print(BColors.FAIL + "Warning: fdb_embedded couldn't be imported,\n" + \
            "We won't be able to check the Firebird database with our embedded client.\n" \
            + "Make sure you've installed the fdb_embedded package correctly." + BColors.ENDC)
            return

        self.db_filepath = ""
        self.setup_environmentvars("~/test", "~/test/CGI.vvv")
        # self.repattern_tumblr_full = re.compile(r'(tumblr_.*_).*\..*') #eg (tumblr_abcdeo1_)raw.jpg
        self.repattern_tumblr = re.compile(r'(tumblr_.*o)[1-10]+_.*\..*') #eg (tumblr_abcdeo)1



    def setup_environmentvars(self, path, mydbfilepath):
        """Sets up the FIREBIRD env var for securty2.fdb lookup"""
        # Point to our current VVV firebird database (for security2.fdb)
        # os.environ['FIREBIRD'] = '~/INSTALLED/VVV-1.3.0-x86_64/firebird'
        # Alternatively, use a copy of the security2.fdb:

        if not FDB_AVAILABLE:
            return False

        os.environ['FIREBIRD'] = path
        self.db_filepath = mydbfilepath
        print(BColors.WARNING + 'setup_environmentvars():\nFIREBIRD set:' + \
        os.environ['FIREBIRD'] + "\nmydbfilepath:" + self.db_filepath + BColors.ENDC)
        return True


    def parse_clipboard_content(self, board_content):
        """isolate filename from URIs, extensions and whatnot,
        returns dic{'validwords', 'count', 'original_string'} """
        if not FDB_AVAILABLE:
            return False

        board_content = board_content.split("\n")[0] #we stop at the first newline found
        length = len(board_content)
        if length <= 5 or length > 180: #arbitrary 4 character long?
            return None
        else:
            #TODO: figure out a better optimized way of parsing these
            if "https://" in board_content or "http://" in board_content:
                #select only last item, minus extension
                print("last item in url: " + board_content.split("/")[-1])
            if "tumblr" in board_content:
                result = self.repattern_tumblr(board_content)
                print("tumblr filename: " + board_content + result)

            valid_dict = {'found_words': '', 'count': '', 'original_query': board_content}

            valid_dict['found_words'], valid_dict['count'] = self.get_set_from_result(board_content)
            return valid_dict


    def get_set_from_result(self, word):
        """Search our FDB for word
        returns set(found_set), int(found_count)"""
        print("\nget_set_from_result(): looking for: |" + word + "|\n")
        found_set = set()
        found_count = 0
        # con1 = services.connect(user='sysdba', password='masterkey')
        # print("Security file for database is: ", con1.get_security_database_path() + "\n")

        con = fdb.connect(
            database=self.db_filepath,
            # dsn='localhost:~/test/CGI.vvv', #localhost:3050
            user='sysdba', password='masterkey'
            #charset='UTF8' # specify a character set for the connection
        )

        # Create a Cursor object that operates in the context of Connection con:
        cur = con.cursor()

        if "'" in word: # we need to add an extra for SQL statements
            word = word.replace("'", "''")

        word = word.upper() # for case insensitive search

        # SELECT = "select * from FILES WHERE FILE_NAME LIKE '%" + word + ".%'" # adding period to include start of extension
        # adding UPPER for case insensitive
        SELECT = "select * from FILES WHERE UPPER (FILE_NAME) LIKE '%" + word + "%'"

        try:
            cur.execute(SELECT)

            for row in cur:
                print(BColors.OKGREEN + "FDB found: " + row[1] + BColors.ENDC)
                found_set.add(row[1])
                found_count += 1

            print(BColors.OKGREEN + "found_count: " + str(found_count) + BColors.ENDC)
            con.close()
            return found_set, found_count

        except Exception as identifier:
            errormesg = "Error while looking up: " + word + "\n" + str(identifier)
            print(BColors.FAIL + errormesg + BColors.ENDC)
            return found_set, found_count

# if __name__ == "__main__":
#     OBJ = FDBquery()

# MEMO:
# not used:
# os.putenv("FIREBIRD", "~/INSTALLED/VVV-1.3.0-x86_64/")
# os.system("export FIREBIRD='~/INSTALLED/VVV-1.3.0-x86_64/firebird'")

# print('INFO:', con.db_info(fdb.isc_info_user_names))

# Execute the SELECT statement on tables:
# "FILE_NAME, FILE_EXT, FILE_SIZE, FILE_DATETIME, PATH_FILE_ID, PATH_ID, FILE_DESCRIPTION) VALUES ("
# LIKE, STARTING WITH, CONTAINING, SIMILAR TO

# Look for fields containing word (with any number of chars before and after), if only starting with, use word% instead
# SELECT2 = "select * from FILES WHERE FILE_NAME LIKE (?)" # Suggestion: use STARTING WITH instead of LIFE?
# wordparam = list()
# wordparam.append(word)
# cur.execute(SELECT2, wordparam) #requires a list or tuple

# Look for ANY of the words
# SELECT = "select * from FILES WHERE FILE_NAME LIKE '%word1%' OR FILE_NAME LIKE '%word2%'"

# Look for BOTH words to be present
# SELECT = "select * from FILES WHERE FILE_NAME LIKE '%word1%' AND FILE_NAME LIKE '%word2%'"

# Retrieve all rows as a sequence and print that sequence:
# print(cur.fetchall())



