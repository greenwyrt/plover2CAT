# Translate tape

Plover2CAT can read strokes from a Plover2CAT tape file or paper tape saved from Plover itself and translate the strokes into text. 

First make sure that Plover is enabled. Then select a file through `Translate Tape` under `Steno Actions`, and then select whether the tape file is in `Plover2CAT` format (with `|` characters separating time and other information from the stroke) or normal `Plover` paper/raw tape format. Only a tape file that is not the transcript's own tape file can be selected. If the format select is not correct, errors will occur.

Plover2CAT will then read the strokes from the tape and translate the strokes, using the set of enabled dictionaries present in Plover. If they are no the desired dictionaries to use, set the desired dictionaries first.

