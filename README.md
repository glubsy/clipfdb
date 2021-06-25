Fork of [Clipster](https://github.com/mrichar1/clipster), with added classes to automatically search a local database
for matches in CLIPBOARD clipboard (Linux only).

# How to use

1. Create one or more Firebird databases with [VVV (Virtual Volume View)](http://vvvapp.sourceforge.net)

2. Point to the directory holding security2.fdb, and your databases (two separate config items) in the config file which should be placed in `~/.config/clipfdb`

3. Install dependencies: in a venv: `pip install virtualenv && virtualenv -p python3 --system-site-packages venv && source venv/bin/activate` and `pip install -r requirements.txt`

4. start `start_daemon.sh`, preferably with a key binding (in i3: exec --no-startup-id "/path/to/start_daemon.sh") to toggle on/off. Can be started with argument "venv" to automatically find and activate a python virtualenv.

Files which have been found in the databases will be either printed to terminal (if started from one and config option is active)
or/and simply display as a notification through your notification server (dunst, xfce4-notifyd, etc.) with optional sound effect.

Note: the configuration for the clipboard monitoring part is still located in `~/.config/clipfdb/clipster.ini` for now

# Dependencies

These can be installed automatically with `pip install -r -requirements.txt`:

* The firebird python driver [fdb](https://pypi.org/project/fdb/) or [fdb_embedded](https://github.com/andrewleech/fdb_embedded) (but that one seems deprecated). Install with either `pip install fdb` for the former or `git clone https://github.com/andrewleech/fdb_embedded.git` for the latter (or clone this repo with `--recurse` to download that as a submodule).

* [notify2](https://pypi.python.org/pypi/notify2) (optional) or notify-send and a notifcation daemon (ie. dunst): `pip install notify2`. Warning: requires dbus python bindings, `pacman -S python-dbus` in Arch Linux.

* [simpleaudio](https://pypi.python.org/pypi/simpleaudio/) to play sounds (optional) or paplay `pip install simpleaudio`.


# TIPS

Create config directory ~/.config/clipfdb/ and copy clipfdb.conf.

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

* Remove clipster code and only keep the very basic for hooking the clipboard,
or keep it as a submodule?

* Better error handling (ie. invalid options)

* Make firebird sql databases ourselves?
