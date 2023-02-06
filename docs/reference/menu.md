# Menu

The menu bar in Plover2CAT resides at the top of the page, and each menu section has a drop-down menu of items or sub-menus of items. 

## Descriptions

### The File menu

This menu contains items related to transcript file management, import and export.

- New: Creates a timestamped folder named `transcript-YYYY-MM-DDTHHMMSS` and sets up the editor for writing.
- Open...: Load a previously created `transcript-YYYY-MM-DDTHHMMSS` by Plover2CAT by selecting the `*.config` file in the project folder.
- Import RTF/CRE: Import a RTF/CRE transcript file from other CAT software. See [Supported RTF/CRE features](rtf_support.md) for details.
- Save: Saves the transcript data.
- Save Transcript Data at ...: Save the transcript JSON in another location.
- Export As: This submenu lists the different export formats available for export. For details of each file type, see [export formats](export.md)
- Open Transcript Folder: Open the folder where the transcript is located using the file explorer.
- Close: Closes the transcript.
- Quit: Quits Plover2CAT.

### The Edit Menu

- Find/Replace Pane: Shows the "Find and Replace" pane if visible.
- Undo: Undo one action ie merge, cut if available.
- Redo: Redo the undone action if available.
- Copy: Copy text (and underlying steno) from paragraph.
- Cut: Cut text (and underlying steno) from paragraph.
- Paste: Paste text (and underlying steno) into paragraph.
- Normal Copy: Copies text only.
- Jump to Paragraph...: Activates a dialog window to select a paragraph to nagivate to.
- Insert Normal Text: Activates a dialog window to insert normal text
- Reset Paragraph: Removes all paragraph text and steno data. Used as the last option when text and steno data go out of sync.

### The Steno Actions Menu

This menu is for steno-related menu items.

- Merge Paragraphs: Merges two paragraphs together.
- Split Paragraphs: Splits one paragraph into two.
- Autocompletion: Start up autocompletion. Requires a `wordlist.json` in a `sources/` dictionary.
- Add Autocompletion Term: Activates dialog window to add autocompletion candidate and steno.
- Retroactive Define: Define an outline after writing it.
- Define Last: Define last preceding untranslate before cursor.
- Lock Cursor at End: If checked, the cursor will be placed at end during writing, and all text is "appended" to end of document. 
- Capture All Steno Input: If checked, all writing through Plover will be tracked, and text emitted into editor, regardless of whether editor window is in focus. By default, no writing to editor when window is not in focus.
- Translate Tape: Activates file dialog selector for tapes files to translate using the present dictionary stack in Plover.

### The Audiovisual Menu

This menu contains items related to audiovisual files.

- Open Audiovisual: Open a file dialog to select an audio file.
- Play/Pause: Play and pause the audio depending on the present state.
- Stop: Stop the audio, returning to the beginning.
- Skip Forward: Skip the audio forward by 5 seconds.
- Skip Back: Skip the audio back by 5 seconds.
- Speed Up: Increase the playback rate by 0.02.
- Slow Down: Decrease the playback rate by 0.02.
- Show/Hide Video: If a video file is selected to be played, then a video window will pop-up. This will show/hide the video window.
- Record/Pause: Start recording using the settings in the audio recording box. If already recording, pressing this will pause recording, which is not the same as to press Stop Recording.
- Stop Recording: Stop any recording in progress.  If Record/Pause is pressed again, the present audio file is overwritten.

### The Styling Menu

- Select Style File: Select the JSON/ODT file containing desired styles to use
- Create New Style: Create a new style based on the currently selected style. User will input new style name.
- Generate Style File From Template: Generate a JSON style file from an ODF or RTF file.
- Refresh Editor: Update the visual styling foreach paragraph if not already done.

### The Dictionary Menu

This menu is for transcript dictionary management.

- Add Custom Dict: Add a custom dictionary to the transcript. See  [transcript dictionaries](#transcript-dictionaries) for details.
- Remove Transcript Dictionary: Removes a loaded transcript dictionary. This will remove both from the Plover instance and the configuration file, but not delete the actual file.

### The View Menu

This menu contains items related to view.

- Zoom In: Increase the zoom on the main editor. The size from this and `Zoom Out` are "temporary", meaning they will fall back to normal if a document is loaded, such as opening/closing projects.
- Zoom Out: Decrease the zoom on the main editor.
- Show All Characters: Toggle to view whitespace charactes (spaces with dots, tabs with left arrows, paragraph endings with pilcrow symbol)
- Window Font: Set the font and size for the window. This is saved when exiting and will be maintained across sessions.
- Paper Tape Font: Set the font and size for the paper tape. This is savd when exiting and will be maintained across sessions.
- Docks: Submenu with items to toggle the visibility of each dock. A user can also right click on the toolbar and toggle dock visibility that way.

### The Help Menu

This menu contains help:

- About: Dialog displaying name and version number.
- Online User Manual: Directs to the online user manual (this document).
- Acknowledgements

## Identifiers

This section documents each menu item under its menu section with the identifier for the action used in Qt and the default shortcut key combinations. These shortcuts can be changed through a JSON file with key combinations as [outlined here](../howto/setcustomshortcuts.md)

### File

| Item                                   | Action Identifier            | Shortcut |
|----------------------------------------|------------------------------|----------|
| New                                    | `actionNew`                  | Ctrl+N   |
| Open...                                | `actionOpen`                 | Ctrl+O   |
| Import RTF/CRE                         | `actionImportRTF`            |          |
| Save                                   | `actionSave`                 | Ctrl+S   |
| Save Transcript Data at...             | `actionSaveAs`               |          |
| Export as... \> Plain Text (.txt)      | `actionPlainText`            |          |
| Export as... \> Plain ASCII (.txt)     | `actionPlainASCII`           |          |
| Export as... \> ASCII (.txt)           | `actionASCII`                |          |
| Export as... \> HTML (.html)           | `actionHTML`                 |          |
| Export as... \> SubRip (.srt)          | `actionSubRip`               |          |
| Export as... \> OpenDocumentText(.odt) | `actionODT`                  |          |
| Export as... \> RTF/CRE (*.rtf)        | `actionRTF`                  |          |
| Open Transcript Folder                 | `actionOpenTranscriptFolder` |          |
| Close                                  | `actionClose`                |          |
| Quit                                   | `actionQuit`                 | Ctrl+Q   |

### Edit

| Item                 | Action Identifier        | Shortcut     |
|----------------------|--------------------------|--------------|
| Find/Replace Pane    | `actionFindReplacePane`  | Ctrl+F       |
| Undo                 | `actionUndo`             | Ctrl+Z       |
| Redo                 | `actionRedo`             | Ctrl+Y       |
| Copy                 | `actionCopy`             | Ctrl+C       |
| Cut                  | `actionCut`              | Ctrl+X       |
| Paste                | `actionPaste`            | Ctrl+V       |
| Normal Copy          | `actionNormalCopy`       | Ctrl+Shift+C |
| Jump to Paragraph... | `actionJumpToParagraph`  |              |
| Insert Normal Text   | `actionInsertNormalText` | Insert       |
| Reset Paragraph      | `actionClearParagraph`   |              |

### Steno Actions

| Item                    | Action Identifier             | Shortcut     |
|-------------------------|-------------------------------|--------------|
| Merge Paragraphs        | `actionMergeParagraphs`       |              |
| Split Paragraph         | `actionSplitParagraph`        |              |
| Autocompletion          | `actionAutocompletion`        |              |
| Add Autocompletion Term | `actionAddAutocompletionTerm` | Ctrl+Alt+R   |
| Retroactive Define      | `actionRetroactiveDefine`     | Ctrl+R       |
| Define Last             | `actionDefineLast`            | Ctrl+Shift+R |
| Lock Cursor At End      | `actionCursorAtEnd`           |              |
| Capture All Output      | `actionCaptureAllOutput`      |              |
| Translate Tape          | `actionTranslateTape`         |              |

### Audiovisual

| Item             | Action Identifier     | Shortcut     |
|------------------|-----------------------|--------------|
| Open Audiovisual | `actionOpenAudio`     | Ctrl+Shift+O |
| Play/Pause       | `actionPlayPause`     | Ctrl+P       |
| Stop             | `actionStopAudio`     | Ctrl+W       |
| Skip Foward      | `actionSkipForward`   | Ctrl+L       |
| Skip Back        | `actionSkipBack`      | Ctrl+J       |
| Speed Up         | `actionSpeedUp`       | Ctrl+Shift+G |
| Slow Down        | `actionSlowDown`      | Ctrl+Shift+S |
| Show/Hide Video  | `actionShowVideo`     |              |
| Record/Pause     | `actionRecordPause`   | Ctrl+Shift+P |
| Stop Recording   | `actionStopRecording` |              |

### Styling

| Item                              | Action Identifier                 | Shortcut |
|-----------------------------------|-----------------------------------|----------|
| Select Style File...              | `actionStyleFileSelect`           |          |
| Create New Style                  | `actionCreateNewStyle`            |          |
| Generate Style File From Template | `actionGenerateStyleFromTemplate` |          |
| Refresh Editor                    | `actionRefreshEditor`             |          |

### Dictionary

| Item                   | Action Identifier            | Shortcut |
|------------------------|------------------------------|----------|
| Add Custom Dict        | `actionAddCustomDict`        |          |
| Remove Transcript Dict | `actionRemoveTranscriptDict` |          |

### View

| Item                    | Action Identifier         | Shortcut |
|-------------------------|---------------------------|----------|
| Zoom In                 | `actionZoomIn`            | Ctrl+=   |
| Zoom Out                | `actionZoomOut`           | Ctrl+-   |
| Show All Characters     | `actionShowAllCharacters` |          |
| Window Font             | `actionWindowFont`        |          |
| Paper Tape Font         | `actionPaperTapeFont`     |          |
| Docks \> Paper Tape     | `actionPaperTape`         |          |
| Docks \> Suggestions    | `actionSuggestions`       |          |
| Docks \> History        | `actionHistory`           |          |
| Docks \> Reveal Steno   | `actionRevealSteno`       |          |
| Docks \> Audio Controls | `actionAudioControls`     |          |
| Docks \> Toolbox        | `actionToolbox`           |          |

### Help

| Item                    | Action Identifier         | Shortcut |
|-------------------------|---------------------------|----------|
| About                   | `actionAbout`             |          |
| Online User Manual      | `actionUserManual`        | F1       |
| Acknowledgements        | `actionAcknowledgements`  |          |