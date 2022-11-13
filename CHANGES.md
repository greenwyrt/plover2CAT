CHANGES

2022-11-13:

- Feature: Text cursor in editor is now 5 pixels wide for visibility.
- Feature: Double-click on stroke in Paper Tape dock, and text cursor in main editor will move to that position if available. This will navigate even if the stroke has been erased and replaced.
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