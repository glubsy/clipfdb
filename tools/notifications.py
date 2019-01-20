#!/usr/bin/python3
"""Notification subsystem"""
import subprocess
import json
# from ast import literal_eval
try:
    import notify2
    NOTIFY2 = True
except ImportError:
    NOTIFY2 = False


class Notifier2():
    """notification object"""

    def __init__(self):
        notify2.init("clipboard")
        # DEBUG
        # info = notify2.get_server_info()
        # caps = notify2.get_server_caps()
        # print("info:\n" + json.dumps(info))
        # print("caps:\n" + json.dumps(caps))
        # self.sendnotification("FDB_QUERY")

    def sendnotification(self, dictionary):
        if dictionary is not None:
            found_words = ""
            for item in dictionary['found_words']:
                found_words += item + "\n"
            count = dictionary['count']
            summary = "Found: " + count + " for " + dictionary['original_query']
            formatted_msg = found_words
            notif = notify2.Notification(summary,
                                         formatted_msg,
                                         "dialog-information" # Icon name in /usr/share/icons/
                                        )
            notif.show()


class Notifier():
    """Use notify-send to pass notifications to notification server (ie. dunst)"""
    def __init__(self):
        pass

    def notify_send_wrapper(self, dictionary):
        """sends dictionary['valid_words', 'count', 'original_word'] to notify-send"""

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
