Fork of [Clipster](https://github.com/mrichar1/clipster), with added classes to automatically search a local database
for matches in CLIPBOAD clipboad (Linux only).

# Dependencies
--* [fdb_embedded](https://github.com/andrewleech/fdb_embedded) (mandatory) (git clone https://github.com/andrewleech/fdb_embedded.git)
--* [notify2](https://pypi.python.org/pypi/notify2) (optional) or notify-send. A notifcation daemon (ie. dunst). (pip install notify2)
--* [simpleaudio](https://pypi.python.org/pypi/simpleaudio/) to play sounds (optional) or paplay (pip install simpleaudio)


# TODOs
--* Wipe out most of Clipster methods we don't need
--* make our own firebird sql database
--* make fdb_embedded an optional dependency by using a true Firebird server
