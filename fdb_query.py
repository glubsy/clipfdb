#!/bin/env python3
from os import environ, path, sep
import re
# import sys
from subprocess import run, CalledProcessError
# import json
from operator import itemgetter
from locale import setlocale, strxfrm, LC_ALL
from argparse import BooleanOptionalAction, ArgumentParser
from configparser import ConfigParser
# from ast import literal_eval
from urllib import parse
# import typing

from constants import BColors

try:
    import fdb
    # import fdb_embedded as fdb
except ImportError as e:
    print(f"Error importing fdb: {e}")
    print(BColors.FAIL + "Warning: fdb_embedded couldn't be imported,\n" + \
            "We won't be able to check the Firebird database with our embedded client.\n" \
            + "Make sure you've installed the fdb_embedded package correctly." + BColors.ENDC)
    raise

try:
    import notify2
    NOTIFY2_AVAIL = True
except ImportError as e:
    print(f"Error importing notify2: {e}")
    NOTIFY2_AVAIL = False

try:
    import simpleaudio
    SA_AVAIL = True
except ImportError:
    SA_AVAIL = False


class FDBController():
    """Handles querying VVV firebird databases locally"""

    def __init__(self):
        args, _ = parse_args()
        self.config = init_config(args)
        self.is_disabled = False

        self.wants_terminal_output = self.config.getboolean('clipfdb', "terminal_output")

        if not self.wants_terminal_output \
        and not self.config.getboolean('clipfdb', 'sound_notifications') \
        and not self.config.getboolean('clipfdb', 'notifications'):
            self.is_disabled = True
            return

        self.notifier = Notifier(self.config)
        self.snd_notifier = SoundNotifier(self.config)

        self.snd_notifier.play(self.snd_notifier.startup_sound)

        # Sets up the FIREBIRD env var for securty2.fdb lookup
        # Point to our current VVV firebird database (for security2.fdb)
        # environ['FIREBIRD'] = '~/INSTALLED/VVV-1.3.0-x86_64/firebird'
        # Alternatively, use a copy of the security2.fdb in that path:
        # TODO we could have a separate security2.fdb files for each database
        environ['FIREBIRD'] = self.config.get('clipfdb', 'security2_path')
        # TODO add to config file options for alternative sorting
        setlocale(LC_ALL, "")

        self.db_handles = []
        # Ignore the "clipfdb" top section
        for db_section in self.config.sections()[1:]:
            self.db_handles.append(
                FDB(
                    self.config.get(db_section, 'filepath'),
                    self.config.get(db_section, 'username'),
                    self.config.get(db_section, 'password'),
                    self.config
                )
            )

    def exit(self):
        """Called from Clipster Daemon."""
        if getattr(self, "snd_notifier", None) is not None:
            self.snd_notifier.play(self.snd_notifier.shutdown_sound)
        # self.parent.exit()
        # sys.exit(0)

    def query(self, clipboard_str):
        """Starts the query process to FDB databases"""

        if self.is_disabled:
            return

        if len(clipboard_str) > 200:
            return

        filtered = filter_content(clipboard_str)

        if not filtered:
            return

        _q = []

        for db in self.db_handles:
            query_dict = {}
            query_dict['db_filename'] = db.db_filename
            query_dict['original_query'] = filtered
            try:
                query_dict['found_words'],\
                query_dict['count'] = db.query(filtered, db.con)
            except Exception as e:
                print(f"{BColors.FAIL}{e}{BColors.ENDC}")
                continue
            _q.append(query_dict)

            if self.wants_terminal_output:
                print_to_stdout(query_dict)

        # TODO separate thread for concurency / event loop
        for query in _q:
            self.notifier.notify(query)
            if query['count'] > 0:
                self.snd_notifier.play(self.snd_notifier.success_sound)
            else:
                self.snd_notifier.play(self.snd_notifier.failure_sound)


# e.g. (tumblr_abcdeo1_)raw.jpg
# repattern_tumblr_full = re.compile(r'(tumblr_.*_).*\..*')
# e.g. (tumblr_abcdeo)10_raw.jpg
repattern_tumblr = re.compile(r'(tumblr_.*o)[1-9]+_.*\..*', re.I)
# e.g. (tumblr_inline_abcdeo)_540.jpg
repattern_tumblr_inline = re.compile(r'(tumblr_inline_.*)_.{3,4}.*', re.I)
repattern_tumblr_redirect = re.compile(r't\.umblr\.com\/redirect\?z=(.*)&t=.*', re.I)
repattern_extensions = re.compile(r'^(.*)(?:\.(?:mp4|webm|avi|mov|mkv|zip|rar|7z|gif|jpeg|jpg|png))$', re.I)


def filter_content(clipboard_str):
    """isolate filename from URIs, extensions and whatnot,
    returns dic{'validwords', 'count', 'original_string'} """

    line = clipboard_str.split("\n")[0] # we stop at the first newline found
    if len(line) < 4: # skip if under 4 characters
        return None

    if "mega.nz/file" in line:
        return None

    reresult = repattern_tumblr_redirect.search(line)
    if reresult: #matches t.umblr redirects
    #if "t.umblr.com/redirect" in board_content:
        #result = parse.unquote(result.split("?z=")[1].split("&t=")[0])
        line = parse.unquote(reresult.group(1))

    if "tumblr" in line:
        reresult = repattern_tumblr.search(line)
        if reresult: # matches regular tumblr url
            line = reresult.group(1)
        else:
            reresult = repattern_tumblr_inline.search(line)
            if reresult: # matches inline url
                line = reresult.group(1)

    if line.endswith("/"):
        line = line[:-1]

    # try:
    #     parsedurl = parse.urlparse(line)
    #     if parsedurl.scheme == "http" or parsedurl.scheme == "https":
    #         # prevent unquoting if not actual http url, might not be so useful
    #         line = parse.unquote_plus(parsedurl.path)
    # except Exception as e:
    #     print(e)

    if line.find("http://") != int(-1) or line.find("https://") != int(-1):
        result = line.split("/")[-1]
        #FIXME more params possible here, only one hardcoded case!
        if result.find("?"):
            line = line.split("?image=")[-1]

        line = parse.unquote_plus(line)

    # Dirty way or removing trailing slash if there's one
    line = line.split("/")[-1]

    # Remove known extensions
    ext = repattern_extensions.search(line)
    if ext:
        line = parse.unquote(ext.group(1))

    # Still too short for query
    if line == '' or len(line) < 4:
        return None
    return line


class FDB():
    """Handle to a Firebird database."""
    def __init__(self, databasepath, username, password, config):
        self.db_filepath = databasepath
        self.db_filename = databasepath.split("/")[-1]
        self.username = username
        self.password = password

        self.max_results = config.getint('clipfdb', "max_results")
        self.wants_parent_directories = config.getboolean('clipfdb', "parent_directories")
        self.con = self.init_connection()

    def init_connection(self):
        con = None
        try:
            con = fdb.connect(
            database=self.db_filepath,
            # dsn='localhost:~/test/CGI.vvv', #localhost:3050
            user=self.username, password=self.password,
            # charset='UTF8' # specify a character set for the connection
            # workaround if libfbclient is not getting along with firebird server, need uninstalled
            # fb_library_name="/usr/lib/python3.7/site-packages/fdb_embedded/lib/libfbclient.so" #HACK HACK
            # Or in case we still can't find it somehow (with fdb pypi package)
            # fb_library_name="/usr/lib/libfbclient.so" #HACK HACK
        )
        except Exception as e:
            print(f"Error initializing connection to {self.db_filename}: {e}")
            con = None  # redundant?
        return con

    def make_select(self, query_str):
        # Add quotes after single quote to escape for SQL statements
        if "'" in query_str:
            query_str = query_str.replace("'", "''")

        # Case insensitivity
        query_str = query_str.upper()

        limit = f"FIRST {self.max_results}" if self.max_results > 0 else ""

        # For some reason this does not work...
        # SELECT = r"""select FILES.FILE_NAME, FILES.FILE_SIZE, FILES.PATH_ID from FILES WHERE UPPER (FILE_NAME) LIKE '%?%'"""
        # stmt = cur.prep(SELECT)

        return "select " + limit + " FILE_NAME, FILE_SIZE, PATH_ID from FILES WHERE UPPER \
(FILE_NAME) LIKE '%" + query_str + "%'"

    def query(self, query_str, con):
        """Search our FDB for word
        returns set(result_list), int(found_count)"""

        if not con:
            con = self.init_connection()
            if not con:
                raise Exception(f"Failed connection to database {self.db_filename}")
            self.con = con

        # print("DEBUG get_set_from_result(): looking for: |" + queryobj.query_dict['original_query'] + "|")
        # con1 = fdb.services.connect(user='SYSDBA', password='masterkey')
        # print("Security file for database is: ", con1.get_security_database_path() + "\n")
        # print(f"Active connections: {con1.get_connection_count()}")

        cur = con.cursor()

        SELECT = self.make_select(query_str)

        # print(f"DEBUG current active transactions: {con.get_active_transaction_count()}")

        result_list = []
        result_dirs = set()
        found_count = 0
        try:
            # cur.execute(stmt, (query_str,))
            for row in cur.execute(SELECT):
                # print(f'{BColors.OKGREEN}Row: {row[0]} {str(row[1])} {row[2]}{BColors.ENDC}')
                result_list.append([row[0], row[1], row[2]])
                result_dirs.add(row[2])

                found_count += 1
                # Obsolete way of limiting result output
                # if found_count >= self.max_results:
                #     break

            # result_list.sort(key=itemgetter(0, 1)) #sort alphabetically, then by size, but ignore case
            # Sort alphabetically, case insensitive:
            result_list.sort(key=locale_keyfunc(itemgetter(0)))
            # print(BColors.OKGREEN + "DEBUG found_count: " + str(found_count) + BColors.ENDC)
            # print(BColors.OKGREEN + "DEBUG result_list: " + str(result_list) + BColors.ENDC)

            # Retrieve parent directory as well
            if self.wants_parent_directories:
                directory_dict = {}
                # Assign pathnames corresponding to each path_id
                for path_id in result_dirs:
                    directory_dict[path_id] = strip_to_basepath(
                        get_directory_value_from_db(self.con, path_id))

                # replace path_id in our result with pathname
                for item in result_list:
                    if directory_dict.get(item[2]) is not None:
                        item[2] = directory_dict.get(item[2])
        except Exception as e:
            print(f"{BColors.FAIL}Error while looking up: {query_str}: {e}{BColors.ENDC}")
        # finally:
            # con.close()
        return (result_list, found_count)


def strip_to_basepath(pathstr):
    """Strip down full pathname to parent directories only"""
    if pathstr is None:
        # might happen if not found?
        return ""
    _list = pathstr.split("/")

    if 1 < len(_list) and len(_list[1:]) > 0:
        # not a single directory, but we can omit the root dir safely
        return "/".join(_list[1:])
    elif len(_list) == 1:
        return _list[0]
    else:
        return "/".join(_list) # unnecessary?


def get_directory_value_from_db(con, dir_id):
    """Retrieve the full path corresponding to PATH_ID from VVV's procedure"""
    cur = con.cursor()
    try:
        cur.execute("EXECUTE PROCEDURE SP_GET_FULL_PATH( ?, ? )",(dir_id, "/"))
    except Exception as e:
        print(f"Error in SP_GET_FULL_PATH: {e}")
    return cur.fetchone()[0]


def locale_keyfunc(keyfunc):
    """Use Locale for sorting"""
    def locale_wrapper(obj):
        return strxfrm(keyfunc(obj))
    return locale_wrapper


def print_to_stdout(query_dict):
    """do pretty text output"""
    result_list = ""
    color = BColors.FAIL
    if query_dict.get('count', 0) > 0:
        for item, size, pardir in query_dict['found_words']:
            result_list += "".join([item,"\t",bytes_2_human_readable(size),"\t",str(pardir),"\n"])
            color = BColors.OKGREEN

    print(f"Found {color}{query_dict.get('count')}{BColors.ENDC} \
for \"{BColors.BOLD}{query_dict.get('original_query')}\"{BColors.ENDC} \
in {BColors.BOLD}{query_dict.get('db_filename')}{BColors.ENDC}\n\
{color}{result_list}{BColors.ENDC}")


class Notifier():
    def __init__(self, config):
        self._provider = None
        if not config.getboolean('clipfdb', 'notifications'):
            return

        if config.get('clipfdb', 'notification_provider') == "notify2"\
        and NOTIFY2_AVAIL:
            self._provider = Notifier2()
        else:
            self._provider = SPNotifier(config)

    def notify(self, message):
        if self._provider is None:
            return
        return self._provider.notify(message)


class SPNotifier():
    """Use a subprocess to send notification (notifier-send by default)"""
    def __init__(self, config):
        self.process_unavail = False
        self.process_name = config.get('clipfdb', 'notification_provider',
                                       fallback='notify-send')
        if not self.process_name:
            print(f"Error. Notification provider \"{self.process_name}\" is incorrect.")
            self.process_unavail = True
            return
        print(f"Using subprocess \"{self.process_name}\" for desktop notifications.")

    def notify(self, message):
        """Pass dict['valid_words', 'count', 'original_word']."""

        if self.process_unavail:
            return

        if message['count'] > 0:
            category = 'clipfdb_found'
        else:
            category = 'clipfdb_notfound'

        found_words = ""
        summary = "".join(("For ", message['original_query'],
                           " in ", message['db_filename']))

        for item, size, pardir in message['found_words']:
            found_words += "".join([item, " ", bytes_2_human_readable(size),
                                    " ", str(pardir), "\n"])

        try:
            # cmd = ['notify-send', '-c', category, '-i', 'dialog-information', summary, found_words]
            cmd = [self.process_name, '-c', category, summary, found_words]
            run(cmd,
                shell=False,
                # check=True,
                stdout=None, stderr=None)
        # except CalledProcessError as e:
        #     print(f"Process \"{self.process_name}\" error: {e}")
        #     self.process_unavail = True
        except Exception as e:
            print(f"Error from \"{self.process_name}\": {e}")
            self.process_unavail = True


class Notifier2():
    """Use notify2 library."""
    def __init__(self):
        notify2.init("clipboard")
        self.timeout = 5000  # 5 seconds
        print(f"Using notify2 library for desktop notifications.")
        # DEBUG
        # info = notify2.get_server_info()
        # caps = notify2.get_server_caps()
        # print("info:\n" + json.dumps(info))
        # print("caps:\n" + json.dumps(caps))
        # self.sendnotification("FDB_QUERY")

    def notify(self, message):
        """sends dict['found_words'] to notification server."""
        found_words = ""
        for item, size, pardir in message['found_words']:
            found_words += "".join([item, " ", bytes_2_human_readable(size),
                                    " ", str(pardir), "\n"])

        count = message['count']
        summary = "".join(("Found: ", str(count), " for ",
                            message['original_query'], " in ",
                            message['db_filename']))

        notif = notify2.Notification(summary,
                                     found_words
                                     # "dialog-information" # Icon name in /usr/share/icons/
                                    )
        notif.timeout = self.timeout
        # Set categories for notif server to display special colours and stuffs
        if count > 0:
            notif.set_category('clipfdb_found')
        else:
            notif.set_category('clipfdb_notfound')
        # notif.set_location(800, 600)  # Not supported by dunst
        try:
            notif.show()
        except Exception as e:
            print(f"Exception in notify2.show(): {e}")


class SoundNotifier():
    def __init__(self, config):
        if config.get('clipfdb', 'sound_provider') == 'simpleaudio' and SA_AVAIL:
            self._provider = SAProvider(config)
        else:
            self._provider = SPProvider(config)

    def play(self, snd):
        if not snd:
            return
        self._provider.play(snd)

    @property
    def success_sound(self):
        return self._provider.success_sound
    @property
    def failure_sound(self):
        return self._provider.failure_sound
    @property
    def startup_sound(self):
        return self._provider.startup_sound
    @property
    def shutdown_sound(self):
        return self._provider.shutdown_sound


class SoundNotificationProvider():
    """Abstract Base Class"""
    def __init__(self, config):
        self.config = config
        self.success_sound = None
        self.failure_sound = None
        self.startup_sound = None
        self.shutdown_sound = None
        self.load_sound_files(config)

    def load_sound_files(self, config):
        pass

    def play(self, snd):
        if not snd:
            return
        self._play(snd)

    def _play(self, snd):
        raise NotImplementedError


class SAProvider(SoundNotificationProvider):
    """Wrapper for simpleaudio library."""
    def load_sound_files(self, config):
        # Only load startup and shutdown sounds unconditionally
        # to play them regardless of config option chosen
        self.startup_sound = self.make_wave(
            config.get('clipfdb', 'startup_sound', fallback=None))
        self.shutdown_sound = self.make_wave(
            config.get('clipfdb', 'shutdown_sound', fallback=None))

        if self.config.getboolean('clipfdb', 'sound_notifications'):
            self.success_sound = self.make_wave(
                config.get('clipfdb', 'success_sound', fallback=None))
            self.failure_sound = self.make_wave(
                config.get('clipfdb', 'failure_sound', fallback=None))

    def make_wave(self, path):
        valid = path_or_none(path)
        if not valid:
            return None
        return simpleaudio.WaveObject.from_wave_file(valid)

    def _play(self, snd):
        played = snd.play()
        played.wait_done()


class SPProvider(SoundNotificationProvider):
    """Wrapper for a subprocess (paplay by default)."""
    def __init__(self, config):
        self.process_unavail = False
        self.process_name = config.get('clipfdb', 'sound_provider',
                                       fallback='paplay')
        if not self.process_name:
            print(f"Error. Sound provider \"{self.process_name}\" is incorrect.")
            self.process_unavail = True
            return
        print(f"Using sound provider \"{self.process_name}\".")
        super().__init__(config)

    def load_sound_files(self, config):
        # Only load startup and shutdown sounds unconditionally
        # to play them regardless of config option chosen
        self.startup_sound = path_or_none(config.get('clipfdb', 'startup_sound', fallback=None))
        self.shutdown_sound = path_or_none(config.get('clipfdb', 'shutdown_sound', fallback=None))

        if self.config.getboolean('clipfdb', 'sound_notifications'):
            self.success_sound = path_or_none(config.get('clipfdb', 'success_sound', fallback=None))
            self.failure_sound = path_or_none(config.get('clipfdb', 'failure_sound', fallback=None))

    def _play(self, snd_path):
        if self.process_unavail:
            return
        try:
            run([self.process_name, snd_path],
                shell=False,
                # check=True,
                stdout=None, stderr=None)
            # out, err = subprocess_call.communicate()
            # ret = subprocess_call.wait() #FIXME: maybe not needed and slows down?
        # except CalledProcessError as e:
        #     print(f"Process error playing {snd_path} with \"{self.process_name}\": {e}")
        #     self.process_unavail = True
        except Exception as e:
            print(f"Error playing {snd_path} with \"{self.process_name}\": {e}")
            self.process_unavail = True


def find_config():
    """Attempt to find config from XDG basedir-spec paths/environment variables."""
    # Set a default directory for clipfdb files
    # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    xdg_config_dirs = environ.get('XDG_CONFIG_DIRS', '/etc/xdg').split(':')
    xdg_config_dirs.insert(0, environ.get(
        'XDG_CONFIG_HOME',
        path.join(environ.get('HOME', path.expanduser("~")), ".config"))
        )
    xdg_data_home = environ.get(
        'XDG_DATA_HOME',
        path.join(environ.get('HOME', path.expanduser("~")), ".local/share")
        )

    data_dir = path.join(xdg_data_home, "clipfdb")
    # Keep trying to define conf_dir, moving from local -> global
    for pathstr in xdg_config_dirs:
        conf_dir = path.join(pathstr, 'clipfdb')
        if path.exists(conf_dir):
            return conf_dir, data_dir
    return "", data_dir


def bytes_2_human_readable(number_of_bytes):
    """Converts bytes into KB/MB/GB/TB depending on value"""
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
    # return path.basename(fullurl)
    fullurl = parse.unquote(fullurl, encoding='utf-8', errors='replace')
    return path.splitext(fullurl)[0]


def isolate_filename(url):
    """remove url, keep file with no ext"""

    fullurl = url[url.rfind("/")+1:]
    # return path.basename(fullurl)
    fullurl = parse.unquote(fullurl, encoding='utf-8', errors='replace')
    return fullurl


def strip_http_keep_filename_noext(mystring):
    """if contains http(s), splits url and keeps last item without extension"""
    if mystring.find("http://") != int(-1) or mystring.find("https://") != int(-1):
        return mystring.split("/")[-1].split(".")[0]
    return mystring


def path_or_none(pathstr):
    if not pathstr or not path.exists(path.expanduser(pathstr)):
        print(f"{BColors.FAIL}{pathstr} does not exist or invalid!{BColors.ENDC}")
        return None
    return path.expanduser(pathstr)


def parse_args():
    """Parse a second time the arguments passed to clipster. But we have to be
    careful not to clash with its namespace regarding our arg names.
    These can be useful to override the values set in the config file."""
    parser = ArgumentParser(description='Clipfdb clipboard content scanner.')

    parser.add_argument('--clipfdb_config', action="store",
                        type=str, default="",
                        help="Path to clipfdb config directory")

    parser.add_argument('--notifications',
                        action=BooleanOptionalAction,
                        type=bool, default=True,
                        help="Enable or disable desktop notifications.")

    parser.add_argument('--terminal-output',
                        action=BooleanOptionalAction,
                        type=bool, default=False,
                        help="Enable or disable messages in stdout.")

    parser.add_argument('--sound-notifications',
                        action=BooleanOptionalAction,
                        type=bool, default=True,
                        help="Enable or disable sound notifications.")

    parser.add_argument('--parent-directories',
                        action=BooleanOptionalAction,
                        type=bool, default=True,
                        help="Enable or disable fecthing parent directories of \
each found item in database.")

    parser.add_argument('--notification-provider', action="store",
                        type=str, default="notify2",
                        # choices=['notify2', 'notify-send'],
                        help="Desktop notification provider: notify2 library or \
notify-send subprocess. [notify2|notify-send|...")

    parser.add_argument('--sound-provider', action="store",
                        type=str, default="simpleaudio",
                        # choices=['simpleaudio', 'paplay'],
                        help="Backend provider to play sounds, either python \
library or external program. [simpleaudio|paplay|...]")

    parser.add_argument('--max-results', action="store",
                        type=int, default=20,
                        help="Maximum number of results to display.")
    return parser.parse_known_args()


def init_config(args):
    """Parse config file, but override values specified from CLI args."""
    conf_dir = args.clipfdb_config
    if not conf_dir:
        conf_dir, _ = find_config()

    # data_dir = path.dirname(__file__)
    config_defaults = {
                        "conf_dir": conf_dir,  # clipfdb config dir
                        "db_filepaths": "", # list of paths to databses files
                        "security2_path": "", # absolute path to security2.fdb
                        "parent_directories": "yes", # retrieve parent directories of files too
                        "max_results": 20, # maximum number of results to report
                        "notifications": "yes",
                        "notification_provider": "notify2", # prefer using notify-send instead of notify2
                        "sound_notifications": "yes",
                        "sound_provider": "simpleaudio", # either paplay or simpleaudio
                        "terminal_output": "no", # output query results to stdout
                        "success_sound": "", # absolute path
                        "failure_sound": "", # absolute path
                        "startup_sound": "", # absolute path
                        "shutdown_sound": "" # absolute path
                        }

    config = ConfigParser(config_defaults)
    config.add_section('clipfdb')
    conf_file = conf_dir + sep + "clipfdb.conf"
    result = config.read(conf_file)
    if not result:
        print("Error trying to load the config file!")

    for key in vars(args):
        config.set('clipfdb', key, str(getattr(args, key)))
    # print(f"{[(k, v) for (k, v) in config.items()]}")
    return config


if __name__ == "__main__":
    # print(f"clipfdb argv: {sys.argv}")
    import clipster
    clipster.main()

# MEMO: (not used)
# putenv("FIREBIRD", "~/INSTALLED/VVV-1.3.0-x86_64/")
# system("export FIREBIRD='~/INSTALLED/VVV-1.3.0-x86_64/firebird'")

# print('INFO:', con.db_info(fdb.isc_info_user_names))

# Execute the SELECT statement on tables:
# "FILE_NAME, FILE_EXT, FILE_SIZE, FILE_DATETIME, PATH_FILE_ID, PATH_ID, FILE_DESCRIPTION) VALUES ("
# LIKE, STARTING WITH, CONTAINING, SIMILAR TO

# Look for fields containing word (with any number of chars before and after), if only starting with, use word% instead
# SELECT2 = "select * from FILES WHERE FILE_NAME LIKE (?)" # Suggestion: use STARTING WITH instead of LIKE?
# wordparam = list()
# wordparam.append(word)
# cur.execute(SELECT2, wordparam) #requires a list or tuple

# Look for ANY of the words
# SELECT = "select * from FILES WHERE FILE_NAME LIKE '%word1%' OR FILE_NAME LIKE '%word2%'"

# Look for BOTH words to be present
# SELECT = "select * from FILES WHERE FILE_NAME LIKE '%word1%' AND FILE_NAME LIKE '%word2%'"

# Retrieve all rows as a sequence and print that sequence:
# print(cur.fetchall())
