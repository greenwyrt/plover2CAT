CHANGES

2022-11-18:
- Feature: A history pane, with click to undo/redo. There is no longer a limit on the number of undo/redo "actions". Logically grouped actions such as replace all can now be undone/redone together. Behind the scenes, management of steno data and writing has been re-implemented into the QUndoStack framework using `QUndoCommand`. (Code is less repetitive, but still repetitive)
- Feature: "Reveal Steno" pane shows the strokes and text underlying the paragraph the cursor is on. 
- Feature: "Reset Paragraph" under the edit menu can be used to delete and paragraph and its associated stroke data. This is most useful if the steno and text ever goes out of sync and the problem cannot be fixed with undo.
- Feature: Dock visibility selection. There is a menu in View --> Docks to select the desired panes to show/hide.
- Change: More "steno-like" actions (Lock Cursor at End, Capture All Steno Input) have been moved to their own menu "Steno Actions".
- Feature: "Retroactive define" under "Steno Actions". Select text overlaying the steno to define. The underlying steno will be set as the "stroke(s)" and a dialog will pop up to input the desired translation. By default, the new dictionary entry will be in the top dictionary (the transcript dict by default). All occurrences of the text string will be replaced by the new translation.
- Feature: "Define Last" will find the closest "untranslate" in the text preceding the cursor, and automatically activate dialog for inputting translation.
- Feature: Autocompletion. A pop-up with possible choices based on what is already written. A `wordlist.json` file is required containing the possible completion choices, and the steno to put. **You need an outline assigned to `{#return}`** to perform selection from the popup. An outine for `\n` will "select" and start a new paragraph.



2022-11-13:

- Feature: Text cursor in editor is now 5 pixels wide for visibility.
- Feature: Select stroke in Paper Tape dock, click "Locate", and text cursor in main editor will move to that position if available. This will navigate even if the stroke has been erased and replaced.
- Feature: Move cursor in main editor with arrow keys, or click to move, and the paper tape dock will scroll to the stroke line matching the time of the stroke under the cursor.
- Feature: Help menu item to link to github user manual.
- Feature: Added tooltips to many more controls/widgets.
- Fix: renamed all PloverCAT mentions to Plover2CAT
- Fix: `audiostarttime` and `audioendtime` inputs in paragraph properties did not update or clear if they did not exist in the data for the paragraph. Now, if property does not exist, it is cleared back to 0 time. Same with `notes`.


2022-11-12

- Fix problem of editor throwing error if "tapey-tape.txt" is not in default location or does not exist.
- New menu item: Lock Cursor at End - if checked, the text cursor is moved to the end at each stroke, and all resulting input is added at end.
- New menu Item: Capture All Steno Input - if checked, text is written to document regardless of whether the editor window is open or not.
- Fixed bug where even if user chose to not quit with unsaved changes, window still closes

2022-11-11

Initial release