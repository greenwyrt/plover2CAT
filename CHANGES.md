CHANGES

ver 1.4.1

- Change: Added status bar messages for importing rtf. When actually parsing rtf file, cursor is set to loading so users know that program is not stuck.

- Bug: Progress bar updates for refresh style and loading transcript were not being processed.

- Bug: ODF export do not have accurate line breaking. Part of this was due to `steno_wrap_plain` not accounting for number of indent spaces properly.

- Bug: ODF export do not have accurate line breaking. Sometimes one word would be squeezed out of the line. The problem is likely the rounding used to estimate max chars per line. The fix is `max char` calculated from text span `- 1` char (which appears to resolve the problem.)

- Feature: Add autocompletion term from within editor. Will reload autocompletion model if autocompletion is enabled. Added documentation.

- Feature: Generate style json from ODT or RTF/CRE files. Added documentation.

- Feature: Headers and footers for export. 

- Feature: Implement `max characters/line` and `max lines per page` for ODF

- Feature: Add `Jump to Paragraph...` to edit menu for fast navigation to specified paragraph by number.

- Bug fix: Thanks @dnaq, [fixed problem](https://github.com/greenwyrt/plover2CAT/pull/1) with type error when interfacing with Qt due to python 3.10 changing extension interface.

ver 1.4.0 (2022-12-19)

- Feature: Rich text editor display
    - Under the hood changes: 
        - QPlainTextEdit --> QTextEdit
        - Styles are imported and qtextblockformats and qtextcharformats are generated off the json file

- Feature: New UI controls in toolbox dock to modify style properties on-the-go. 
If the style file is `json`, the changes are saved. If style file is `odf`, 
changes to style will be purely visual and temporary (exports to odf will use 
original styles from odf, visual changes are lost when editor is closed).

- Feature: "Show All Characters" under the View menu to toggle showing spaces/tabs/paragraph endings.

- Feature: Styling menu
    - Create New Style: create new style will create a new style with user-input name,
      based on the style of the present paragraph. (parent style and other attributes can be edited later)
    - Refresh Editor: Convience function to refresh styling after change in case 
      automatic updates are not working.

- Feature: Insert Plain Text, activated with `Insert` key press. A dialog box for normal 
text to be inserted where cursor is. Good for minor spot insertions. (Will cause trouble 
if `insert` button is called from within Plover - likely rare edge case.)

- Bugfix: Some buttons/controls in gui had `strong focus`, and were being "set off" 
inadvertently when `Enter` was pressed. These controls have been changed to `no focus`.

- Change: For quality of life purposes, json files are now saved in prettified form with 
indentation. Unless there is an enormous json file, there should not be a major impact on file sizes.

- Change: `style file select` moved from toolbox pane to `Styling` menu.

- Change: Some code has been extracted out of `main_window.py`.
    - `constants.py`: contains default dict and default style
    - `helpers.py`: assorted convenience functions such as for unit conversions
    - `qcommands.py`: all the subclassed `qundocommands` used in the editor
    - `rtf_parsing.py`: functions relating to parsing `RTF/CRE` files for import
    - `stroke_funcs.py`: functions for manipulating and editing `stroke_data`

- Change: Icon changed for `Lock Cursor at End`. More icons added for toolbox pages.

- Change: Previous `edit toolbar` is now `steno action toolbar`. New `edit toolbar` 
is populated with common edit actions.

- Feature: Shortcuts to switch styles. The first 10 styles can be applied using 
`Ctrl + [0-9]` (Notice the 0-based index). An example to switch style after new paragraph 
is `end\nQ.{#control(2)}` when the styles in the style selector are `Normal, Question, Answer, Paren`. 
Writing this stroke will add the string `end` to the present paragraph, create a new 
line, inserts `Q.`, and then the `Ctrl+2` emitted by Plover causes the editor to apply the 3rd style, `Answer`.

- Feature: Deleting steno with the `delete` button. Pressing `delete` on the keyboard 
will delete the character to the right of the cursor (if not at end of paragraph) or 
do nothing. If cursor has a selection, pressing `delete` will delete selected text. 
Only works within paragraphs, not across.

- Change: Decreased offset between line number and paragraph if line numbering enabled. (This is hardcoded for now until it is possible to figure out how to not overlap line number and timestamp if they are both enabled and user-set.)

- Change in progress: Moving documentation from user manual to docs file. Organized into tutorials and how to __ articles for now. 

Ver 1.3.0 (2022-11-24)

- Feature: Versioning. Powered by [`dulwich`](https://github.com/jelmer/dulwich/). Versions are made when the transcript is opened, and each time on user save. It is possible to jump back and forth between versions. Only the transcript is modified, the paper tape does not change.
- Change: Transcripts are now in pretty JSON format. Makes it easy to do `diff` between versions for git users.
- Bug fix: pull version from one source for "about" dialog and setup.cfg
- Possible fix for lag, uncertain.

Ver 1.2.2 (2022-11-22):
- Feature: Context menu (right click) for editing.
- Change: Made the light gray of selection in paper tape and alternating elements in reveal steno "darkGray" instead.
- Feature: Spellcheck with the `spylls` library, ability to select from dictionaries in `spellcheck`
- Bug fix: style setting complains about lack of block data when setting style on new paragraph

Ver 1.2.1 (2022-11-20):
- Bug fix: Menu bar is now non-native. Otherwise, some menu items might get eaten up on macOS (thanks yann).
- Bug fix: Reset paragraph now has a critical warning dialog before executing. It will also erase action history for the session.
- Bug fix: Disable steno actions when no transcript is open. 
- Feature: Style setting in paragraphs now an undo-able action
- Bug fix: Fixed ODF problem exporting due to checking fonts.
- Feature: Icons for select menu items. Tool bars were getting too big, and icons save space.


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