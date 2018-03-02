Fork of [Clipster](https://github.com/mrichar1/clipster), with added classes to automatically search a local database
for matches in CLIPBOAD clipboad (Linux only).

# How to use

1. Create one or more Firebird databases with [VVV (Virtual Volume View)](http://vvvapp.sourceforge.net)

2. Point to the directory holding security2.fdb, and your databases (two separate config items)

3. start start_daemon.sh, preferably with a key binding (in i3: exec --no-startup-id "/path/to/start_daemon.sh") to toggle on/off

Files which have been found in the databases will be either printed to terminal (if started from one and config option is active)
or/and simply display as a notification through your notification server (dunst, xfce4-notifyd, etc.) with optional sound effect.


# Dependencies

* [fdb_embedded](https://github.com/andrewleech/fdb_embedded) (mandatory) (git clone https://github.com/andrewleech/fdb_embedded.git)

* [notify2](https://pypi.python.org/pypi/notify2) (optional) or notify-send. A notifcation daemon (ie. dunst). (pip install notify2)

* [simpleaudio](https://pypi.python.org/pypi/simpleaudio/) to play sounds (optional) or paplay (pip install simpleaudio)


# TIPS

Configure dunst for colored output depending on results.
Example below, disables icon, makes body bold and green / red on found / nothing found

```
[clipfdb_found]
    category = "clipfdb_found"
    background = "#005500"
    foreground = "#ffffff"
    format = "%s\n<b>%b</b>"
    new_icon = off

[clipfdb_notfound]
    category = "clipfdb_notfound"
    background = "#550000"
    foreground = "#ffffff"
    format = "%s\n<b>%b</b>"
    new_icon = off
```


# TODOs

* Wipe out most of Clipster methods we don't need (branch clipster_clean)

* Catch up with latest changes in clipster (blacklist, whitelist)

* Better error handling (ie. invalid options)

* make our own firebird sql database

* make fdb_embedded an optional dependency by using a true Firebird server
