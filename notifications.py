#!/usr/bin/python3
"""Notification subsystem"""
import subprocess
# from ast import literal_eval

class Notifier():
    """handles communications with notifications daemon"""
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
