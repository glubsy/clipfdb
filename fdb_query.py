#!/usr/bin/python3
import os
import re
# from fdb import services
import subprocess
import json
# from ast import literal_eval

from constants import BColors
try:
    import fdb_embedded as fdb
    # from fdb_embedded import services
    FDB_AVAILABLE = True
    try:
        import notify2
        NOTIFY2_AVAIL = False
    except ImportError:
        NOTIFY2_AVAIL = False
except ImportError:
    FDB_AVAILABLE = False


class FDBEmbedded():
    """Handles querying VVV firebird databases locally"""

    def __init__(self):
        if not FDB_AVAILABLE:
            print(BColors.FAIL + "Warning: fdb_embedded couldn't be imported,\n" + \
            "We won't be able to check the Firebird database with our embedded client.\n" \
            + "Make sure you've installed the fdb_embedded package correctly." + BColors.ENDC)
            self.fdb_avail = False
            return

        self.fdb_avail = True
        self.db_filepath = ""
        self.setup_environmentvars("~/test", "~/test/CGI.vvv")
        # self.repattern_tumblr_full = re.compile(r'(tumblr_.*_).*\..*') #eg (tumblr_abcdeo1_)raw.jpg
        self.repattern_tumblr = re.compile(r'(tumblr_.*o)[1-10]+_.*\..*') #eg (tumblr_abcdeo)1

        self.notifyinstance = Notifier2()
        self.queryobj = FDBQuery()



    def setup_environmentvars(self, path, mydbfilepath):
        """Sets up the FIREBIRD env var for securty2.fdb lookup"""
        # Point to our current VVV firebird database (for security2.fdb)
        # os.environ['FIREBIRD'] = '~/INSTALLED/VVV-1.3.0-x86_64/firebird'
        # Alternatively, use a copy of the security2.fdb:

        os.environ['FIREBIRD'] = path
        self.db_filepath = mydbfilepath
        print(BColors.WARNING + 'setup_environmentvars():\nFIREBIRD set:' + \
        os.environ['FIREBIRD'] + "\nmydbfilepath:" + self.db_filepath + BColors.ENDC)
        return True


    def query_databases(self, board_content):
        """Starts the query process to FDB databases"""

        if not self.fdb_avail:
            return

        self.queryobj.activate()

        self.queryobj.originaltext = board_content
        self.parse_clipboard_content(self.queryobj.originaltext)

        if self.queryobj.is_active:
            self.notifyinstance.init_send_notification(self.queryobj.validated_dict)



    def parse_clipboard_content(self, board_content):
        """isolate filename from URIs, extensions and whatnot,
        returns dic{'validwords', 'count', 'original_string'} """

        board_content = board_content.split("\n")[0] #we stop at the first newline found
        length = len(board_content)
        if length <= 5 or length > 180: #arbitrary 4 character long?
            self.queryobj.is_active = False
            return
        else:
            #TODO: figure out a better optimized way of parsing these
            if "https://" in board_content or "http://" in board_content:
                #select only last item, minus extension
                print("last item in url: " + board_content.split("/")[-1])
            if "tumblr" in board_content:
                result = self.repattern_tumblr(board_content)
                print("tumblr filename: " + board_content + result)

            self.queryobj.validated_dict['original_query'] = board_content

            self.queryobj.validated_dict['found_words'], self.queryobj.validated_dict['count'] = self.get_set_from_result(board_content)
            return


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


class FDBQuery():
    """a query object"""

    def __init__(self):
        self.is_active = False
        self.originaltext = ""
        self.validated_dict = {'found_words': '', 'count': '', 'original_query': ''}

    def activate(self):
        self.is_active = True



class Notifier2():
    """notification sender object"""

    def __init__(self):
        if NOTIFY2_AVAIL:
            notify2.init("clipboard")
        # DEBUG
        # info = notify2.get_server_info()
        # caps = notify2.get_server_caps()
        # print("info:\n" + json.dumps(info))
        # print("caps:\n" + json.dumps(caps))
        # self.sendnotification("FDB_QUERY")

    def init_send_notification(self, dictionary):
        """choose between libnotify2 or notify-send depending on import resulsts"""
        if NOTIFY2_AVAIL:
            self.notify2_notify(dictionary)
        else:
            self.notify_send_wrapper(dictionary)


    def notify2_notify(self, dictionary):
        """sends dictionary['found_words'] to notification server"""
        if not NOTIFY2_AVAIL:
            return
        if dictionary is not None:
            found_words = ""
            for item in dictionary['found_words']:
                found_words += item + "\n"
            count = dictionary['count']
            summary = "Found: " + str(count) + " for " + dictionary['original_query']
            formatted_msg = found_words
            notif = notify2.Notification(summary,
                                         formatted_msg,
                                         "dialog-information" # Icon name in /usr/share/icons/
                                        )
            notif.timeout = 30000 #show for 30 seconds
            #notif.set_location(800, 600) #not supported by dunst
            notif.show()


    def notify_send_wrapper(self, dictionary):
        """Fallback method in case notify2 couldn't be imported
        sends dictionary['valid_words', 'count', 'original_word'] to notify-send"""

        #FIXME: add summary and formatting like notify2
        strings = ', '.join(str(e) for e in dictionary['found_words'])

        print("STRINGS: ", strings)
        try:
            cmd = ['notify-send', strings]
            # subprocess_call = subprocess.Popen(cmd, shell=,False, stdout=logfile, stderr=logfile)
            subprocess_call = subprocess.Popen(cmd, shell=False, \
            stdout=None, stderr=None)
            out, err = subprocess_call.communicate()
            # ret_code = subprocess_call.wait()
            ret_code = subprocess_call.wait()
            print("notifier_send_wrapper() return code: " + str(ret_code))
            return ret_code
        except Exception as e:
            print("Exception notifier_send_wrapper(): " + str(e))
            return 1
        return 1
