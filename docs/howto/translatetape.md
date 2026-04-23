# Translate tape

Plover2CAT can read strokes from a Plover2CAT tape file or paper tape saved from Plover itself and translate the strokes into text. 

Go to **Steno Actions** and then **Translate Tape** on the top menu.

1. Make sure that Plover is enabled and set the desired dictionaries.

2. A dialog box will appear. Click the `Select File` button to select a tape file to import.

2. Select a file in the file selector popup.

3. Select whether the tape file is in `Plover2CAT` format (with `|` characters separating time and other information from the stroke) or normal `Plover` paper/raw tape format. The entire tape is loaded together. If the tape file is the transcript's own tape, note that any changes to the tape will not be imported.

4. Once the tape is loaded on the right pane, select the line to start. By default, the first line is selected. Use `Translate One`, `Translate 10` or `Translate All Succeeding` which will translate the selected line, selected line and 9 following strokes, or selected and all remaining strokes in tape. 

5. To undo a stroke, use the `Undo Last` button. 

Because plover2CAT resets the Plover translator everytime the tape translate dialog is used, it is not always possible to resume the same transation after exiting the dialog. This has the greatest effect if the dialog was exited in the middle of a multi-stroke word since the translator does not remember the preceding strokes the second time around.

It is possible to re-translate the same strokes over and over by re-selecting the same lines in the tape. However, depending on the state of the Plover translator, the output may not be the same.