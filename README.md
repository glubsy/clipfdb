This is a hack around [Clipster](https://github.com/mrichar1/clipster), with the added functionality to automatically search local databases for text received from the "CLIPBOARD" clipboard (Linux with Xorg only). This is achieved via a simple hook added to clipster.

# How to use

1. Create one or more Firebird databases with [VVV (Virtual Volume View)](http://vvvapp.sourceforge.net)

2. Copy the default config file **clipfdb.conf** into `~/.config/clipfdb/`. Edit it to point to the directory holding **security2.fdb**, as well as your databases and credentials.

3. Install required dependencies.
Either system-wide or in a venv like this:
```
pip install virtualenv && virtualenv -p python3 --system-site-packages venv
source ./venv/bin/activate
pip install -r requirements.txt
```

1. start `start_daemon.sh`, preferably with a key binding to toggle it on/off. The Clipster client can also be used as usual.
For example in i3 config file:
```
bindsym $mod+Shift+i exec --no-startup-id "/path/to/clipfdb/start_daemon.sh --venv --no-terminal-output"
bindsym $mod+c exec --no-startup-id "/path/to/clipfdb/clipster/clipster -sc"
```
The shell script can be started with argument **--venv** to automatically find and activate a python venv.

Files which have been found in the databases will be either printed to terminal (if started from one and is not suppressed by argument --no-terminal-output)
or/and simply displayed as a notification through your notification server of choice (dunst, xfce4-notifyd, etc.) with optional sound effect.

Options can be overridden via command-line arguments.

Note: the configuration for Clipster is still valid and and used. It should be in `~/.config/clipster/clipster.ini`.

# Dependencies

These can be installed automatically with `pip install -r -requirements.txt`:

* The Firebird super-server, preferrably a version compatible with the databases created by VVV (most likely 2.5 currently).

* The Firebird python driver [fdb](https://pypi.org/project/fdb/) or [fdb_embedded](https://github.com/andrewleech/fdb_embedded). But note that it seems to be deprecated. It's kept as a submodule here for the time being, clone this repo with `--recurse` and get ready to fix it yourself.

* [notify2](https://pypi.python.org/pypi/notify2) (optional) or notify-send and a notification daemon (ie. dunst).
Warning: requires dbus python bindings, `pacman -S python-dbus` in Arch Linux.

* [simpleaudio](https://pypi.python.org/pypi/simpleaudio/) (optional) or paplay to play sound notifications.
Actually any process can be called in place of paplay.

# Tips

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


# TODO

* Try not to rely on clipster anymore, especially for future Wayland support.

* Write a module to generate Firebird SQL databases ourselves.

* Allow other SQL databases through API abstraction.
