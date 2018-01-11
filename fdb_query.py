#!/usr/bin/python3
import os
import re
# from fdb import services
import subprocess
# import json
# import operator
from operator import itemgetter
from locale import setlocale, strxfrm, LC_ALL
import configparser
# from ast import literal_eval
from urllib import parse

from constants import BColors
try:
    import fdb_embedded as fdb
    # from fdb_embedded import services
    FDB_AVAILABLE = True
    try:
        import notify2
        NOTIFY2_AVAIL = True
    except ImportError:
        NOTIFY2_AVAIL = False

    try:
        import simpleaudio
        SA_AVAIL = True
    except ImportError:
        SA_AVAIL = False
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
        self.config = self.init_config()
        self.db_filepaths = self.config.get('clipfdb', 'db_filepaths').split(",")
        self.setup_environmentvars(self.config.get('clipfdb', 'security2_path'))
        self.wants_notifications = self.config.getboolean('clipfdb', 'notifications')
        self.wants_sound_notifications = self.config.getboolean('clipfdb', 'sound_notifications')
        self.wants_terminal_output = self.config.getboolean('clipfdb', "terminal_output")

        if not self.wants_terminal_output and not self.wants_sound_notifications and not self.wants_notifications:
            self.fdb_avail = False
            return # no use using us!

        # self.repattern_tumblr_full = re.compile(r'(tumblr_.*_).*\..*') #eg (tumblr_abcdeo1_)raw.jpg
        self.repattern_tumblr = re.compile(r'(tumblr_.*o)[1-9]+_.*\..*', re.I) #eg (tumblr_abcdeo)10_raw.jpg
        self.repattern_tumblr_inline = re.compile(r'(tumblr_inline_.*)_.{3,4}.*', re.I) #eg (tumblr_inline_abcdeo)_540.jpg

        # initialize objects instances
        if self.wants_notifications:
            self.notifyinstance = Notifier2()
            if self.config.getboolean('clipfdb', 'use_notify_send'):
                self.notifyinstance.prefer_notify_send = True

        self.query_ojects = list()

        for item in self.db_filepaths: #generate as many objects as there are databases to query
            self.query_ojects.append(FDBQuery(item))

        if self.wants_sound_notifications:
            self.soundnotifinstance = SoundNotificator()
            if self.config.getboolean('clipfdb', 'use_paplay'):
                self.soundnotifinstance.prefer_paplay = True
            self.soundnotifinstance.init_vars(\
            os.path.expanduser(self.config.get('clipfdb', 'success_sound')), \
            os.path.expanduser(self.config.get('clipfdb', 'failure_sound')))



    def init_config(self):
        conf_dir = os.path.dirname(os.path.realpath(__file__))
        conf_file = conf_dir + os.sep + "clipfdb.conf" #TODO: make config path configurable (need argv?)
        successsound = conf_dir + os.sep + 'sounds' + os.sep + '340259__kaboose102__blippy-02_short.wav'
        failuresound = conf_dir + os.sep + 'sounds' + os.sep + '340259__kaboose102__blippy-01_short.wav'
        config_defaults = {"db_filepaths": "", # list of paths to databses files
                           "security2_path": "", # absolute path to security2.fdb
                           "notifications": "yes",
                           "use_notify_send": "no", # prefer using notify-send instead of notify2
                           "sound_notifications": "yes",
                           "use_paplay": "no", # prefer using paplay instead of simpleaudio
                           "terminal_output": "no", # output query results to stdout
                           "success_sound": successsound, # absolute path to success sound file
                           "failure_sound": failuresound # absolute path to failure sound file
                          }

        config = configparser.SafeConfigParser(config_defaults)
        config.add_section('clipfdb')
        result = config.read(conf_file)
        if not result:
            print("Error trying to load the config file!")
        return config


    def setup_environmentvars(self, path):
        """Sets up the FIREBIRD env var for securty2.fdb lookup"""
        # Point to our current VVV firebird database (for security2.fdb)
        # os.environ['FIREBIRD'] = '~/INSTALLED/VVV-1.3.0-x86_64/firebird'
        # Alternatively, use a copy of the security2.fdb in that path:
        os.environ['FIREBIRD'] = path
        setlocale(LC_ALL, "") #TODO: add to config options for sorting?

        return True


    def query_databases(self, board_content):
        """Starts the query process to FDB databases"""

        if not self.fdb_avail:
            return

        for queryobj in self.query_ojects:
            queryobj.activate()

        parsed_content = self.parse_clipboard_content(board_content)


        for queryobj in self.query_ojects:
            if not queryobj.is_disabled:
                queryobj.response_dict['original_query'] = parsed_content
                self.get_set_from_result(queryobj)

        # notifications:
        for queryobj in self.query_ojects:
            if queryobj.is_active and not queryobj.is_disabled:
                if self.wants_notifications:
                    self.notifyinstance.init_send_notification(queryobj)
                if self.wants_sound_notifications:
                    self.soundnotifinstance.init_send_sound(queryobj)



    def parse_clipboard_content(self, board_content):
        """isolate filename from URIs, extensions and whatnot,
        returns dic{'validwords', 'count', 'original_string'} """

        board_content = board_content.split("\n")[0] # we stop at the first newline found
        length = len(board_content)
        if length < 4 or length > 180: #arbitrary 3 character long?
            for queryobj in self.query_ojects:
                queryobj.is_disabled = True #query is too short
            return
        else:
            result = board_content
            if "tumblr" in board_content:
                reresult = self.repattern_tumblr.search(board_content)
                if reresult: # matches regular tumblr url
                    result = reresult.group(1)
                else:
                    reresult = self.repattern_tumblr_inline.search(board_content)
                    if reresult: # matches inline url
                        result = reresult.group(1)
            result = strip_http_keep_filename_noext(result)
            if result is '':
                for queryobj in self.query_ojects:
                    queryobj.is_disabled = True
                return

            return result


    def get_set_from_result(self, queryobj):
        """Search our FDB for word
        returns set(found_list), int(found_count)"""

        # print("DEBUG get_set_from_result(): looking for: |" + queryobj.response_dict['original_query'] + "|")
        found_list = list()
        found_count = 0
        # con1 = services.connect(user='sysdba', password='masterkey')
        # print("Security file for database is: ", con1.get_security_database_path() + "\n")

        con = fdb.connect(
            database=queryobj.db_filepath,
            # dsn='localhost:~/test/CGI.vvv', #localhost:3050
            user='sysdba', password='masterkey'
            #charset='UTF8' # specify a character set for the connection
        )

        # Create a Cursor object that operates in the context of Connection con:
        cur = con.cursor()

        # we need to add an extra for SQL statements
        if "'" in queryobj.response_dict['original_query']:
            querystring = queryobj.response_dict['original_query'].replace("'", "''")

        querystring = queryobj.response_dict['original_query'].upper() # for case insensitive search

        # adding UPPER for case insensitive
        select_stmt = "select FILE_NAME, FILE_SIZE from FILES WHERE UPPER (FILE_NAME) LIKE '%" \
        + querystring + "%'"

        try:
            cur.execute(select_stmt)

            for row in cur:
                # print(BColors.OKGREEN + "DEBUG FDB found: " + row[0] + " " + str(row[1]) + BColors.ENDC)
                found_list.append((row[0], row[1]))
                found_count += 1
                if found_count > 20: #maximum results returned
                    break

            # found_list.sort(key=itemgetter(0, 1)) #sort alphabetically, then by size, but ignore case
            found_list.sort(key=self.locale_keyfunc(itemgetter(0))) #sort alphabetically, CI
            # print(BColors.OKGREEN + "DEBUG found_count: " + str(found_count) + BColors.ENDC)
            # print(BColors.OKGREEN + "DEBUG found_list: " + str(found_list) + BColors.ENDC)
            con.close()
            queryobj.response_dict['found_words'], queryobj.response_dict['count'] \
            = found_list, found_count

        except Exception as identifier:
            errormesg = "Error while looking up: " + queryobj.response_dict['original_query'] \
            + "\n" + str(identifier)
            print(BColors.FAIL + errormesg + BColors.ENDC)
            queryobj.is_disabled = True

        if self.wants_terminal_output:
            self.print_to_stdout(queryobj)


    def locale_keyfunc(self, keyfunc):
        """use Locale for sorting"""
        def locale_wrapper(obj):
            return strxfrm(keyfunc(obj))
        return locale_wrapper


    def print_to_stdout(self, queryobj):
        """do pretty text output"""
        found_list = ""
        if queryobj.response_dict['count'] > 0:
            for item, size in queryobj.response_dict['found_words']:
                found_list += item + "\t" + bytes_2_human_readable(size) + "\n"
                color = BColors.OKGREEN
        else:
            color = BColors.FAIL
        print("Found " + color + str(queryobj.response_dict['count']) + BColors.ENDC + \
              " for \'" + BColors.BOLD \
              + queryobj.response_dict['original_query'] + "\'" + BColors.ENDC \
              + " in " + BColors.BOLD + queryobj.db_filename + BColors.ENDC + "\n" \
              + color + found_list + BColors.ENDC)

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

    def __init__(self, databasepath):
        self.is_active = False
        self.is_disabled = True
        self.db_filepath = databasepath
        self.db_filename = databasepath.split("/")[-1]
        self.response_dict = {'found_words': '', 'count': '', 'original_query': ''}

    def activate(self):
        self.response_dict = {'found_words': '', 'count': '', 'original_query': ''}
        self.is_active = True
        self.is_disabled = False


class Notifier2():
    """notification sender object"""

    def __init__(self):
        if NOTIFY2_AVAIL:
            notify2.init("clipboard")
        self.timeout = 5000
        self.prefer_notify_send = False
        # DEBUG
        # info = notify2.get_server_info()
        # caps = notify2.get_server_caps()
        # print("info:\n" + json.dumps(info))
        # print("caps:\n" + json.dumps(caps))
        # self.sendnotification("FDB_QUERY")

    def init_send_notification(self, obj):
        """choose between libnotify2 or notify-send depending on import resulsts"""
        if NOTIFY2_AVAIL and not self.prefer_notify_send:
            self.notify2_notify(obj)
        else:
            self.notify_send_wrapper(obj)


    def notify2_notify(self, obj):
        """sends dictionary['found_words'] to notification server"""

        found_words = ""
        for item, size in obj.response_dict['found_words']:
            found_words += item + " " + bytes_2_human_readable(size) + "\n"
        count = obj.response_dict['count']
        summary = "Found: " + str(count) + " for " + \
        obj.response_dict['original_query'] + " in " + obj.db_filename
        notif = notify2.Notification(summary,
                                     found_words,
                                     "dialog-information" # Icon name in /usr/share/icons/
                                    )
        notif.timeout = self.timeout #show for 5 seconds
        # Set categories for notif server to display special colours and stuffs
        if count > 0:
            notif.set_category('fdb_query_found')
        else:
            notif.set_category('fdb_query_notfound')
        #notif.set_location(800, 600) #not supported by dunst
        try:
            notif.show()
        except Exception as e:
            print("Exception while notif.show():" + str(e))


    def notify_send_wrapper(self, obj):
        """Fallback method in case notify2 couldn't be imported
        sends dictionary['valid_words', 'count', 'original_word'] to notify-send"""

        if obj.response_dict['count'] > 0:
            category = 'fdb_query_found'
        else:
            category = 'fdb_query_notfound'

        found_words = ""
        summary = "For " + obj.response_dict['original_query'] + " in " + obj.db_filename

        for item, size in obj.response_dict['found_words']:
            found_words += item + " " + bytes_2_human_readable(size) + "\n"

        try:
            cmd = ['notify-send', '-c', category, '-i', 'dialog-information', summary, found_words ]
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



class SoundNotificator():
    """Plays a sound after query"""

    def __init__(self):
        self.prefer_paplay = False
        self.success_sound = ""
        self.failure_sound = ""

    def init_vars(self, success_sound, failure_sound):
        """initializes sound file paths in vars"""
        if SA_AVAIL and not self.prefer_paplay:
            self.success_sound = simpleaudio.WaveObject.from_wave_file(success_sound)
            self.failure_sound = simpleaudio.WaveObject.from_wave_file(failure_sound)
        else:
            self.success_sound = success_sound
            self.failure_sound = failure_sound

    def init_send_sound(self, obj):
        """devide what to use"""
        if SA_AVAIL and not self.prefer_paplay:
            self.sa_method(obj)
        else:
            self.paplay_method(obj)


    def sa_method(self, obj):
        """use simpleaudio to play sound"""
        if not obj.response_dict['count']:
            play_obj = self.failure_sound.play()
            play_obj.wait_done()
        else:
            play_obj = self.success_sound.play()
            play_obj.wait_done()


    def paplay_method(self, obj):
        """fallback method using paplay"""
        if not obj.response_dict['count']:
            argz = self.failure_sound
        else:
            argz = self.success_sound
        try:
            cmd = ['paplay', argz]
            # subprocess_call = subprocess.Popen(cmd, shell=,False, stdout=logfile, stderr=logfile)
            subprocess_call = subprocess.Popen(cmd, shell=False, \
            stdout=None, stderr=None)
            out, err = subprocess_call.communicate()
            # ret_code = subprocess_call.wait()
            ret_code = subprocess_call.wait()
            # print("paplay_method() return code: " + str(ret_code))
            return ret_code
        except Exception as e:
            print("Exception paplay_method(): " + str(e))
            return 1
        return 1


# UTILS
def bytes_2_human_readable(number_of_bytes):
    if number_of_bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step_to_greater_unit = 1024.

    number_of_bytes = float(number_of_bytes)
    unit = 'bytes'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'KB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'MB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'GB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'TB'

    precision = 1
    number_of_bytes = round(number_of_bytes, precision)

    return str(number_of_bytes) + ' ' + unit


def isolate_filename_noext(url):
    """remove url, keep file with no ext"""

    fullurl = url[url.rfind("/")+1:]
    # return os.path.basename(fullurl)
    fullurl = parse.unquote(fullurl, encoding='utf-8', errors='replace')
    return os.path.splitext(fullurl)[0]


def isolate_filename(url):
    """remove url, keep file with no ext"""

    fullurl = url[url.rfind("/")+1:]
    # return os.path.basename(fullurl)
    fullurl = parse.unquote(fullurl, encoding='utf-8', errors='replace')
    return fullurl


def strip_http_keep_filename_noext(mystring):
    """if contains http(s), splits url and keeps last item without extension"""
    if mystring.find("http://") or mystring.find("https://"):
        return mystring.split("/")[-1].split(".")[0]
    return mystring
