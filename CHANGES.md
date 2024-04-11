# CHANGES

## Ver 3.0.0:

This version is refactored to separate editor internals and the GUI to implement new features.

New Features:

- Each transcript is now a tab, and multiple tabs (transcripts) can be open at once
- Copy and paste between different transcripts
- Transcript names can be any text string accepted by operating system
- Updates to a paragraph's properties such as creation time are now undo-able
- Page format parameters (including header/footer) for config can be "undone" and "redone", and saved once cursor is moved away from box
- Use Sphinx for documentation

New GUI changes: 

- Revert to previous versions moved to edit menu from History dock, uses dialog window instead
- Audio controls are now disabled unless media is loaded
- Video from media now appears in the `Audio Controls` dock rather than separate window
- Millisecond adjustment for audio can now be set to negative values (previously lowest value was 0)
- Audio recording settings removed from dock, now as a dialog from menu
- Transcripts can be closed from File menu and also by button on tab
- Changes to styling only allowed if JSON style file loaded


Bugs:

- Fix bug where video window did not close after editor did by moving video into dock
- Warning if new created style has same name as an existing style, does not proceed to create style
- steno_search name conflict fixed by renaming button
- fixed problem when direction was foward and steno search would not detect next match in paragraph
- Do not copy image with same name if one exists in `assets` already
- image asset files are no longer absolute (causes problems when changing names / using save as)
- fixed incorrects paths in docs

Known Issues:

- RTF imports do not work properly if no style in the form of `\sn` is defined for each paragraph
- When inserting image, two image files cannot have same name (copying second will mean replacing first with another, possibly different, image)


## Ver 2.3.3:

- Change: add default port 4455 for OBS
- Bug: caption worker with obs no longer throws error if port is empty (create client if set to OBS)
- Remote captions on twitch successfully tested with https://localhost.run/
- Change: updated [caption how-to](docs/howto/captions.md) with new instructions for remote captions

## Ver 2.3.2:

- Fix bug with import OBSSDKRequestError

## Ver 2.3.1:

This is the last planned update for version2.x.x unless there are major bugs.

- Changed: renamed View menu to Preferences

- Changed: Move Edit Menu Shortcut to Preferences Menu

- Feature: Clipboard history

- Changed: will check and load `JSON` dictionary files from `plover_config/plover2cat/dict` for all transcripts

## Ver 2.3.0

Captioning interface and internals has been changed from 2.2.x versions with the help of @AshenColors.

- Changed: use `deque` for sending captions to achieve "rolling" effect, and fixed repeating words 

- Changed: default max line length 32 and max lines 3 for captioning

- Bug: Fixed flush captions sending extra empty line

- Bug: remove left whitespace from captions

- Changed: When using flush captions, add extra "\n" to force new line in display + remote

- Changed: Changed buffer for captions from character to word

- Bug: clean up `captionWorker` when closing transcript

- Bug: fix problem in saving menu shortcuts when no shortcut.json exists

- Change: also make available spellchecking dictionaries located in `plover_config/plover2cat/spellcheck` for selection

- Change: `Tools` menu to visibility of every tab in Toolbox if hidden

- Change: internal, convert while loops for going through document into for loops using block count

- Feature: "Steno Search", use to find most likely translations based on steno outline

- Feature: add online search for Wikipedia, DuckDuckGo, Google, Merriam-Webster, and Oxford English Dictionary

## Ver 2.2.2

- Feature: Add OBS captioning through `obsws-python`

## Ver 2.2.1 

- Bug: deleted transcripts still in recent, remove from recent files menu if transcript no longer exists.

- Change: export strokes-only paper tape

## Ver 2.2.0 (2023-08-13)

- Change: Style submenu added, now style change shortcuts are visible to user (`Ctrl + {0-9}`) for first ten styles.

- Feature: Keyboard input enabled.

- Feature: Captioning window, with character delay, max line length, and interval.

- Bug: `Capture All Steno Output` had not been logging strokes at the same time. Will now log properly based on setting.

- Bug: Multiple empty line strings were not generating the paragraphs needed, ie `\n\n`

- Change: text elements and stroke elements now have `__add__` and `__radd__`, other classes raise errors. This is used to collapse like-class elements for steno wrapping.

- Change: Window titlebar now updates with transcript name when transcript is opened.

- Bug: removed thread deletion from `export_*` as before, a second export would crash.

## Ver 2.1.1 (2023-08-06)

This is a minor revision as most are under the hood changes

- Change: hookup menu Undo/Redo items to stack, now items will display things like "Redo/Undo insert ..."

- Change: remove unused actions from UI

- Change: New qcommand `style_update` to update style changes, brings style changes into undo framework

- Change: QUndoCommand text messages standardized

- Change: Main editor and dialogs have new/condensed tooltips, docs updated.

- Change: Toolbox Dock now uses tabs (holding scroll areas) rather than pages, less scrolling needed and more space for ui since page titles do not take up vertical space

- Bug: word wrapped text did not return proper times for timestamps, added `split` method to elements

- Bug: fixed RTF parser that did not respect spaces as delimiters vs text, now using new json format

- Bug: fix #10 where editor falls back to default system font, should now fall back to first style font

- Change: SRT export now word-wraps to 47 characters max automatically.

- Change: gather UI updates into `update_gui` to update every cursor move

## Ver 2.1.0 (2023-08-02)

This version focuses mainly on "things" to be inserted.

Editor Changes:

- Feature: Navigate to headings using the Navigation dock by doubleclicking, ODT export has heading styling. Heading levels can be assigned to styles in the styling pane. 

- Feature: User Fields, can be set in editor, and then inserted from menu by shortcut (`Ctrl+Shift+{0-9}`) for first nine defined entries

- Feature: Autosave. Will save the transcript to a hidden file in the transcript directory at user defined interval. Enabled by default.

- Change: suggestions can now be sourced from plover_clippy_2 thanks to @AshenColors 

- Feature: Automatic paragraph prefixes and suffix strings, customizable for each style. 

- Feature: Set shortcuts for menu items right in editor. Does checking to ensure shortcuts are not one already in use or reserved.

- Feature: Insert index text through the indices editor and also with quick menu insertions.

- Feature: New steno action, delete last untrans.

- Change: Zoom in/ zoom out have been removed (non-functional with styling). Font sizes should be changed through styling.

- Feature: Transcript suggestions, search transcript for common n-grams and frequent rare words to add to dictionary.

UI Changes:

- Change: `Define Last` is renamed `Define Last Untrans` in menu

- Change: Reveal steno dock now only shows the text of the elements. Hover to see details such as type. Wrap has been enabled to reduce horizontal scrolling for long paragraphs.

- Feature: Recent Files pane that appears at center at startup, displays recent files to open at a click. 

- Change: Main editor widget is now tabbed between the editor and a recent files pane. When loading a transcript, the editor text only appears after loading is completed (increases speed).

- Change: aligned paper tape, [thanks AshenColors](https://github.com/greenwyrt/plover2CAT/pull/11#issue-1832014437)

Internal Changes:

- Multiple dialog windows with own code and UI to implement new features.

- Change: updated documentation. `user_manual.md` is out-of-date and removed as documentation has been moved and re-organized in `docs/`. Moved to **bold** for menu items. 

- Change: rename `to_dict` of text elements to `to_json`

- Change: reformatted log messages, actions that affect the content are INFO level and as JSON records while GUI events are DEBUG level. Will help with filtering for dev and debugging purposes.

- Change: Element checking in transcript loading for block. If no image elements, skip the `QUndoCommand` interface and directly insert text. This increases loading speed by magnitudes. Also adds block and char formats during initial text insertion, avoid refresh syle for entire document.

- Change: Will ask user to select whether to refresh styles if over 200 blocks as it can take time. Within `set_par_style`, will check elements in block, and if no image element, will set entire block charFormat for speed.

- Change: Keep original json dict in memory, and when a paragraph is edited, use `userState` to mark. This way, `userData` of blocks are only extracted after encountering the first `userState`. If only a few paragraphs are changed (especially at end), drastically decreases saving time since only changed blocks need to get updated in json dict.

- Bug: combine strokes if Plover issues a "correction" (backspaces + string) if # of backspaces greater than previous string emitted. Fixes "dropping" of strokes in transcript data due to the backspaces entire steno elements.


ver 2.0.1

- Bug: removed unused reference to icon in resources
- Bug: chunking for `steno_wrap` was splitting elements, not words, leading to improper wrapping for multi-stroke words.
- Bug: retro/last define bug, ([link](https://github.com/greenwyrt/plover2CAT/pull/6))
- Change: now record audiotime even if media is on pause, previously only occurred when media was playing
- Change: `export_srt` now using same `QTextBlock` iterator as other exports, no longer search for block by number


## Ver 2.0.0 (2023-07-11)

Major change:
- Custom classes to store stroke data and other text elements within `userData` in the `QTextDocument`
- Manipulation of text + steno has been reworked to use new classes
- `stroke_funcs.py` removed since functions are now in the custom classes
-  `export_helpers.py` added, moved export-related helpers out 

- Feature: Customizable background color.

- Feature: Does not allow autocomplete enabled if there is no stroke for `{#Return}` in active dictionaries as using `\n` for confirm choice will cause new paragraph to be inserted.

- Feature: Multi-stroke steno search. The search strokes has to be an exact match, ie `KPH/EU` will match `KPH/EU` but not `KPHEU` or `KPH/E`

- Feature: Reveal steno now shows different labels depending on the type of element. `T` for plain text, `S` for text associated with steno, `I` for an image etc.



## Ver 1.4.2 (2023-02-06)

- Bug: Anodyne reported that setting `after output` or some retroactive commands was throwing errors. This should now be fixed.

- Feature: Read both Plover2CAT style tape, and raw/paper tape saved from Plover.

- Change: Underlying object names for menu actions have been changed to camelCase for all. Previously action names were inconsistent.

- Feature: User can set custom shortcuts for menu actions.

- Change: the `steno_rtf` class that parsed rtf files has been renamed `rtf_steno` as the inversion is more accurate.

- Feature: RTF export (basic features of spec only).

- Change: Documentation has been updated and organized extensively into separate files under docs/ from user_manual.md. The How-To section should cover how to use most menu items. The Online Help menu now directs to the doc folder on github

- Change: Online help now has F1 as the default shortcut.


## Ver 1.4.1 (2022-12-30)

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

## Ver 1.4.0 (2022-12-19)

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

## Ver 1.3.0 (2022-11-24)

- Feature: Versioning. Powered by [`dulwich`](https://github.com/jelmer/dulwich/). Versions are made when the transcript is opened, and each time on user save. It is possible to jump back and forth between versions. Only the transcript is modified, the paper tape does not change.
- Change: Transcripts are now in pretty JSON format. Makes it easy to do `diff` between versions for git users.
- Bug fix: pull version from one source for "about" dialog and setup.cfg
- Possible fix for lag, uncertain.

## Ver 1.2.2 (2022-11-22):
- Feature: Context menu (right click) for editing.
- Change: Made the light gray of selection in paper tape and alternating elements in reveal steno "darkGray" instead.
- Feature: Spellcheck with the `spylls` library, ability to select from dictionaries in `spellcheck`
- Bug fix: style setting complains about lack of block data when setting style on new paragraph

## Ver 1.2.1 (2022-11-20):
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
