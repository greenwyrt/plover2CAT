# Translate tape

Plover2CAT can read strokes from a Plover2CAT tape file or paper tape saved from Plover itself and translate the strokes into text. 

Using the dialog controls, it is possible to translate the entire tape, or select portions. It is also possible to repeatedly translate the same section.

1. Make sure that Plover is enabled and set the desired dictionaries.

2. Select a file through `Translate Tape` under `Steno Actions`.

3. A dialog box will appear. Click the `Select File` button to select a tape file to import.

3. Select whether the tape file is in `Plover2CAT` format (with `|` characters separating time and other information from the stroke) or normal `Plover` paper/raw tape format. The entire tape is loaded together. If the tape file is the transcript's own tape, note that any changes to the tape will not be imported.

4. Once the tape is loaded on the right pane, select the desired beginning stroke. Use `Translate One`, `Translate 10` or `Translate All Succeeding` which will translate the selected stroke, selected and 9 following strokes, or selected and all remaining strokes in tape. 

5. To undo a stroke, use the `Undo Last` button. 


Unlike the undo history in the normal transcript, the history for tape is limited to 50 actions. The undo history is also erased when exiting the dialog.

Because plover2CAT resets the Plover translator everytime the tape translate dialog is used, it is not possible to resume the same transation after exiting the dialog. This has the greatest effect if the dialog was exited in the middle of a multi-stroke word since the translator does not remember the preceding strokes the second time around.