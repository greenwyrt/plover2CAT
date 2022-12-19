# Introduction

Plover2CAT is a plugin for Plover, the open-source stenography engine. If the only user requirement is to write steno on the computer, this plugin is not needed as Plover is more than sufficient. Plover2CAT provides some of the features from computer-aided-transcription (CAT) programs to help produce a transcript for captioning or other purposes. 

# Features Overview:

- [x] a rich text editor with steno hidden underneath
- [x] conventional styling of paragraphs, with formatting translated to exported files such as Open Document Text
- [x] timestamps for each stroke and associated with each piece of text
- [x] conventional editing features such as cut/copy/paste while keeping steno data attached
- [x] undo/redo history
- [x] automatic creation and loading of transcript-specific dictionaries for each transcript
- [x] find and replace for simple text, steno stroke, and untrans.
- [x] retroactive define, and define last translate with replacement of all previous occurrences and new outline sent to transcript dictionary
- [x] an audiovisual player, with controls for timing offset, playback rate, skipping forward and back
- [x] synchronization of steno with the audio/video file for transcription
- [x] audio recording synchronized with steno (file format dependent on codecs in operating system)
- [x] export transcript, with formatting when possible, to plain text, basic ASCII, formatted ASCII, HTML, SubRip, and Open Text Document formats (with style templates)
- [x] saves paper tape with keys pressed, position of cursor in document, and timestamps at each stroke
- [x] suggestions based on stroke history (powered by Tapey Tape), updated every paragraph
- [x] spellcheck using the `spylls` library, ability to select spellcheck dictionaries 
- [x] versioning using the `dulwich` library, switch between previously saved transcript states.
- [x] basic import of RTF/CRE transcript

This plugin is built on Plover and inspired by [plover_cat](https://github.com/LukeSilva/plover_cat). 


# Getting Started

Download the code from this repository. Open the terminal following instructions here [on the command-line](https://github.com/openstenoproject/plover/wiki/Invoke-Plover-from-the-command-line). On Windows, use:

```
 .\plover_console.exe -s plover_plugins install plover2CAT
 ## use install -e for development
```

On MacOS and Unix systems, use `plover` rather than `plover_console.exe`.

## Starting a New Transcript

Open Plover2CAT from within Plover after installation, by Tools --> Plover2CAT. A window with a main editor, and dockable containers for suggestions, paper tape, and other functions will appear. Create a new transcript with File --> New (or `Ctrl + N`). A folder selection dialog will appear. Plover2CAT will create a transcript folder with a timestamp at the selected location.

Once Plover is enabled, writing to the main editor will be possible. The main function of Plover2CAT is for writing steno, and by default, only steno translated by Plover will be written (and deleted with the `*`). 

A custom dictionary for the transcript is loaded into Plover, prepopulated with shortcuts for common actions. When File --> Close is used to close the transcript, the custom dictionary will be removed from Plover.

## Opening an Existing Transcript

Select the `config.CONFIG` in the transcript folder to open the transcript.

## Default CAT behaviour

Check "Lock Cursor at End" and "Capture All Steno Input" to only write to end of document and to still write even when editor window is not in focus. By default, writing is inserted into any part of text, and only when window is in focus.

## Styling and Page Formatting

Plover2CAT comes with preset styles and page formatting. These controls are located in the toolbox dock. Users can see the style of the current paragraph in `Current Paragraph Style`. Switching styles is done by selecting a different style from the drop down. It is also possible to switch among the first 10 styles using `Ctrl + {0,9}`. An example to switch style after new paragraph is `end\nQ.{#control(2)}` when the styles in the style selector are `Normal, Question, Answer, Paren`. Writing this stroke will add the string `end` to the present paragraph, create a new 
line, inserts `Q.`, and then the `Ctrl+2` emitted by Plover causes the editor to apply the 3rd style, `Answer`.

Users can change font, style, alignment and other properties for each paragraph and then pressing `Modify Style` to confirm. The changes will be applied to the whole document for all paragraphs using the style. See [style settings](#style-settings) for an explanation of the controls.

Page dimensions and margins can be changed under the `Page  Format` pane. Options such as `maximum characters per line`, `max lines per page`, `line numbering` and `line timestamps` can be enabled and set for the export formats that support them. (See table in [export formats](#export-formats))

## Opening Audiovisual Files

Select an audio file on the computer by Audio --> Open Audio (`Ctrl + Shift + O`). When audio is playing, steno strokes will be timestamped with the audio time. Open the "Paragraph Properties Editor" in the Toolbox pane to see the timestamps associated with each paragraph.

## Recording Audio

Open "Audio Recording" in the Toolbox Pane to select parameters for recording such as the input device. Click Record/Pause on the toolbar or through Audiovisual --> Record/Pause to start recording. Use Audiovisual --> Stop Recording to stop recording. 

## Saving and Export

The transcript will be saved as an JSON file within the created transcript folder when File --> Save (`Ctrl + S`) is used.

The available export formats are:
  - Open Document Text
  - SubRip
  - Plain ASCII
  - ASCII
  - HTML
  - Plain Text

For more details on each format and supported features, see the relevant section below on [export formats](#export-formats)

## Close Transcript

Use File --> Close to close the transcript and File --> Quit (`Ctrl+Q`) to quit the editor, with optional check to save if changes have been made. **DO NOT** use the `Alt+ F4` or `ESC` as that causes an instant exit without saving.

# Folder Structure

The transcript folder is created through `Create New` on the menu. By default, it is named `transcript-{timestamp}`. Several default folders and files are created within this transcript folder.

The basic structure is:

```
transcript folder/
    audio/
    dictionaries/
        transcript.json
        custom.json
        dictionaries_backup
    exports/
    sources/
    styles/
        default.json
        styles.odf
    transcript.transcript
    transcript.tape
    config.CONFIG
```

Here is a description of what each folder contains (file formats are described in [formats](#formats)):
- audio: audio recording files
- dictionaries: transcript-specific JSON files in Plover dictionary format that will be loaded when the transcript is opened
- exports: not yet implemented, will contain all exported files
- sources: a `wordlist.json` that contains autocomplete suggestions.
- styles: style files (JSON or ODF), used in exporting

The `.tape` file holds all strokes for the transcript.
The `.transcript` file is a JSON holding stroke and styling information for the transcript.
`config.CONFIG` is the configuration file containing settings for the transcript.

# Shortcuts

| Menu Item             | Shortcut         |
|-----------------------|------------------|
| New                   | Ctrl + N         |
| Open                  | Ctrl + O         |
| Save                  | Ctrl + S         |
| Quit                  | Ctrl + Q         |
| Find/Replace Pane     | Ctrl + F         |
| Undo                  | Ctrl + Z         |
| Redo                  | Ctrl + Y         |
| Copy                  | Ctrl + C         |
| Cut                   | Ctrl + X         |
| Paste                 | Ctrl + V         |
| Normal Copy           | Ctrl + Shift + C |
| Retroactive Define    | Ctrl + R         |
| Define Last           | Ctrl + Shift + R |
| Refresh Editor        | F5               |
| Set style 0 - 9       | Ctrl + {0, 9}    |
| Insert Plain Text     | Ins              |
| Delete Char to right  | Del              |
| Open Audiovisual File | Ctrl + Shift + O |
| Play/Pause            | Ctrl + P         |
| Stop                  | Ctrl + W         |
| Skip Forward          | Ctrl + J         |
| Skip Back             | Ctrl + L         |
| Speed Up              | Ctrl + Shift + G |
| Slow Down             | Ctrl + Shift + S |
| Record/Pause          | Ctrl + Shift + P |
| Zoom In               | Ctrl + =         |
| Zoom Out              | Ctrl + -         |

# Layout

Hover with the mouse to see tooltips on items in the window.

![Example of hovering](images/tooltips.gif)

## Status Bar

The status bar at the bottom of the window shows important events and warning messages.

## Main Editor

The main editor is located at the center of the window. This is where the writing shows up. By default, it is not possible to edit the contents of this area using a normal keyboard. The cursor, for now, is always kept at the end of the text when writing.

## Menu

The menu is the top bar of the window. A brief summary is outlined for each menu item. More complicated menu items and their use will be described in the [editing](#editing) section.

### The File Menu

This menu contains items related to file management, import and export.

- New: This creates a timestamped folder named `transcript-YYYY-MM-DDTHHMMSS` and sets up the editor for writing.
- Save: This saves the transcript as a JSON file in the folder.
- Open: This is used to load a previously created `transcript-YYYY-MM-DDTHHMMSS` by Plover2CAT by selecting the `*.config` file in the project folder.
- Import RTF: import a RTF/CRE transcript file from other CAT software. See [Supported RTF Import](#supported-rtf-import) for details.
- Export As: This submenu lists the different export formats. For specifics on each format, see the [formats](#formats) section.
- Close: This closes the transcript.
- Quit: This quits Plover2CAT.

### The Edit Menu

![Example of lock cursor at end](images/lock_cursor.gif)

For more detail, go to the [editing](#editing) section.

- Cut: cut text (and underlying steno) from paragraph.
- Copy: copy text (and underlying steno) from paragraph.
- Paste: paste text (and underlying steno) into paragraph.
- Normal Copy: copies text only.
- Undo: Undo one action ie merge, cut if available.
- Redo: Redo the undone action if available.
- Find/Replace Pane: shows the "Find and Replace" pane if visible. See [Find and Replace](#find-and-replace) section for details.
- Insert normal text: to insert normal text
- Reset Paragraph: Removes all paragraph text and steno data. Used as the last option when text and steno data go out of sync.

### The Steno Actions Menu

This menu is for steno-related menu items.

- Merge Paragraphs: Merges two paragraphs together.
- Split Paragraphs: Splits one paragraph into two.
- Autocompletion: start up autocompletion. Requires a `wordlist.json` in a `sources/` dictionary.
- Retroactive Define: Define an outline after writing it.
- Define Last: Define last preceding untranslate before cursor.
- Lock Cursor at End: If checked, the cursor will be placed at end during writing, and all text is "appended" to end of document. 
- Capture All Steno Input: If checked, all writing through Plover will be tracked, and text emitted into editor, regardless of whether editor window is in focus. By default, no writing to editor when window is not in focus.

### The Styling Menu

- Select style file: Select the JSON/ODT file containing desired styles to use
- Create New Style: Create a new style based on the currently selected style. User will input new style name.
- Refresh Editor: This will update the visual styling foreach paragraph if not already done.

### The Dictionary Menu

This menu is for transcript dictionary management.

- Add Custom Dict: Add a custom dictionary to the transcript. See  [transcript dictionaries](#transcript-dictionaries) for details.
- Remove Transcript Dictionary: Removes a loaded transcript dictionary. This will remove both from the Plover instance and the configuration file, but not delete the actual file.


### The Audiovisual Menu

![Show/Hide video window](images/show_hide_video.gif)

![Skipping and playback rate changes](images/video_slowdown_skip.gif)

This menu contains items related to audiovisual files.

- Open Audiovisual: This opens a file dialog to select an audio file.
- Play/Pause: This plays and pauses the audio depending on the present state.
- Stop: This stops the audio, returning to the beginning.
- Skip Forward: This skips the audio forward by 5 seconds.
- Skip Back: This skips the audio back by 5 seconds.
- Speed Up: This increases the playback rate by 0.02.
- Slow Down: This decreases the playback rate by 0.02.
- Show/Hide Video: If a video file is selected to be played, then a video window will pop-up. This will show/hide the video window.
- Record/Pause: This starts recording using the settings in the audio recording box. If already recording, pressing this will pause recording, which is not the same as to press Stop Recording.
- Stop Recording: This stops any recording in progress.  If Record/Pause is pressed again, the present audio file is overwritten.

### The View Menu

This menu contains items related to view.

- Zoom In: This increases the zoom on the main editor. The size from this and `Zoom Out` are "temporary", meaning they will fall back to normal if a document is loaded, such as opening/closing projects.
- Zoom Out: This decreases the zoom on the main editor.
- Show All Characters: Toggle to view whitespace charactes (spaces with dots, tabs with left arrows, paragraph endings with pilcrow symbol)
- Window Font: This controls the font and size for the window. This is saved when exiting and will be maintained across sessions.
- Paper Tape Font: This controls the font and size for the paper tape. This is savd when exiting and will be maintained across sessions.
- Docks: Toggle the visibility of each dock. A user can also right click on the toolbar and toggle dock visibility that way.

### The Help Menu

This menu contains help:

- Online User Manual: click to go to the online user manual (this document).
- Acknowledgements

One of the goals in future development is to replace the online user manual with an offline manual packaged with the plugin using the QHelpEngine in Qt. 

## Toolbar

![Toolbars can float and move around](images/toolbar.gif)

The toolbar (located under the menu) contains shortcuts to commonly used items in the menu, and each item is described in the [menu](#menu) section. The different segments of the toolbar can be re-arranged or pulled out to float independently.

## Panes

Plover2CAT has multiple panes which are arranged around the main editor on startup. These panes are "dockable", and can be moved independently by clicking and dragging on the window bar. As with all Qt dockable widgets, these panes can be 1) floating, 2) placed on the top, left, right, or bottom of the window, and 3) stacked on top of each other. Each pane can be closed if not needed. To re-open the panes, right-click the toolbar and select the desired pane. 

![Example of moving and stacking docks](images/floating_stacking_docks.gif)

### Paper Tape

This pane shows an alternative version of the Plover Paper Tape.
Each time a stroke is pressed, the stroke is saved to a `.tape` file in the `transcript-YYYY-MM-DDTHHMMSS` folder. 
See [Tape](#tape) for a description of the format.

The paper tape is linked to the text and will scroll to the corresponding stroke when the cursor in the editor moves.

![Example of Linking](images/paper_text_link.gif)

Highlight a stroke in the paper tape, and click "Locate" to move to that position in the main text editor. 

### Suggestions

Plover2CAT uses the [Plover Tapey Tape plugin](https://github.com/rabbitgrowth/plover-tapey-tape) for suggestions, in the default format and in the default location (`tapey-tape.txt`). If the plugin is not installed, or the location and format of the file is not the default, suggestions within Plover2CAT will likely not work. 

Suggestions can be sorted by most common (default), or most recent (toggle the `By Recency` option). 

Entries will show up to the ten most common/recent entries, only if Tapey Tape has suggested an alternative outline thrice before. 

The truly nitty-gritty: for users who have a custom output format defined for Tapey Tape, if `%s` is part of the format, the suggestions should be extracted properly as the regex relies on the presence of the two spaces and `>` before a suggestion.

### Reveal Steno

This is a table which shows the current paragraph's text, and the steno underlying the text. It will update when the cursor moves, and the paragraph is non-empty.

### History

Plover2CAT keeps track of all editing in the editor. The History Pane first lists the actions performed in the session, with new actions appended to the end. Clicking on an action before the end will undo all actions to that action, and clicking below will redo actions. 

The second part of the pane is the "Version History". Here, it is possible to switch to previously saved versions of the transcript. Only the `*.transcript` file is modified, the paper tape is unchanged. For most, the user interface is enough as it provides up to 100 versions to switch to.

Under the hood, versioning is powered by [`dulwich`](https://github.com/jelmer/dulwich/), a purely Python implementation of git. Commits made by the editor are done with the author being "plover2CAT." For power users, they can use all git commands possible, such as assess all the changes through git, revert files past 100 revisions, and even set up remote repositories. (Pushing to remote repositories is outside the scope of this plugin.)


### Audiovisual Controls

By default, the audio controls pane is located at the bottom of the window. 

`Play/Pause` and `Stop` buttons are not part of this pane, they exist in the toolbar and menu. 

The first input box, with default number `1.00x`, is the playback rate. The `Speed Up` and `Slow Down` menu items will increment up/down this number by 0.05.

The second input box, with default `0ms`, is the audio delay, measured in milliseconds. This number represents the difference between the actual position of the audio and the audio time recorded with the steno. For example, if `KAT` was stroked at 1 minute and 23 seconds, and the audio delay is 2 seconds, `KAT` is recorded at being stroked at 1 minute and 21 seconds. There are no shortcuts or menu items to control this. Adjust using the arrow buttons of the input.

The horizontal slider is the track, with time position on the left, and total duration of the track on the right. Move the slider to skip to the desired position.

Codecs may have to be installed on the operating system to play certain audio/video formats.

### Toolbox

The Toolbox pane contains pages of different controls. See the [tools](#tools) section for details.

# Editing

Many of the editing functions work exactly like they do in normal word processors, with certain caveats. The work in keeping the steno organized occur in the background.

## Normal Writing

Write into the editor pane in the middle. The cursor is placed at the end after creating/opening a transcript. Click at other places in the text to move the cursor and insert text.

## Add Custom Dictionary

Select a dictionary from the filesystem and load into Plover2CAT. Use this instead of the Plover Add Dictionary as this will copy the dictionary into the `dict/` folder so it will be loaded and removed from Plover automatically when the transcript is opened or closed while remaining self-contained.

The `default.json` is a good place to add transcript-specific outlines if there is only a few.

## Remove Transcript Dictionary

Plover2CAT keeps track of the transcript dictionary and all other added custom dictionaries. The editor will load them into Plover when the transcript is opened. To remove a dictionary, use this rather than Plover's "Remove Selected Dictionary". A file dialog will open in the transcript's dictionaries directory for selection of a dictionary to remove. This will prevent Plover2CAT from loading the removed dictionary the next time. 

## Split Paragraphs

Click to set the cursor or click and drag to select characters. The "split" will occur at the beginning of the selection or the visible cursor. A newline character sent through Plover will cause the same effect. If the selection includes an entry at the start, and the option `Before Output` for space placement in Plover, then the initial space will be removed in the new paragraph. `space_placement` is set as part of the `config.config` file when the project is first created. This option should not be changed after any steno has been input as it will mess up the underlying steno rearrangements.

## Merge Paragraphs

Select text or place cursor in the *second* of the paragraphs for the merge. This paragraph will be appended to the previous paragraph. By default, an empty space is added between the two paragraphs. Alternatively with the keyboard, set the cursor to the beginning of the second paragraph and stroke to have Plover send a backspace (but a space will not be added inbetween).

## Copy

Selected text and underlying steno will be copied.

## Cut

Selected text and underlying steno will be copied and removed from original paragraph to be pasted.

## Paste

Insert selected text and underlying steno from previous cut/copy actions.

## Normal Copy

This is a convenience for copying to other applications as only *regular text* is copied to clipboard. The above copy/cut do not send anything to the computer clipboard, and only work within the editor itself.

## Undo/Redo

Plover2CAT keeps track of all the actions performed in the editor such as writing, "deleting" and cut/paste. This is visualized in the `History` Pane.

The normal shortcuts `Ctrl + Z` and `Ctrl + Y` can be used to undo/redo. 

## Autocompletion

An autocompletion feature has to be toggled through the Steno Actions menu. The choices for completion have to be provided by a `wordlist.json` in a `sources/` folder within the transcript folder. The format for the file is described in [Wordlist Format](#autocomplete-wordlist). 

Choices can be scrolled using arrow keys on the pop-up. It is **essential** that an outline is mapped to `{#return}` in one of Plover's loaded dictionaries. That outline/stroke has to be used to select the autocomplete choice. Using an outline mapping to `\n` will cause a new paragraph to be started in addition to making the selection.

## Styling

Plover2CAT currently uses a `block-based` styling approach. This means that formatting changes can only be applied to paragraphs, not sections of text within paragraphs. In other words, it's not possible to have two different fonts used within one paragraph.

Font, margins and other common word processor styling can be set through Plover2CAT. Following other word processors, styles can be based on other styles and it is possible to specify the style of the new paragraph following the present one.

# Tools

## Styling

The styling pane contains formatting controls for paragraphs. The styling elements are applied to exported files when possible. Changes will appear visually in the editor (like other word processing software) even if some export formats do not support such formatting.

Default styles are provided in the `default.json` file within the `styles` directory. This file contains text and paragraph properties for the common styles using OpenTextDocument element names, such as "Normal", "Question", and "Answer." The default styles appear under "Current Paragraph Style" drop-down menu when a transcript folder is newly created.

### Style Files

To select a different style file, use `Styling` --> `Select Style File` from the menu, and select the desired style file.

Any ODF elements allowed in the text and paragraph properties can be specified within the `style.json` styles (the odfpy library uses the element name without the hyphens ie `margin-left` to `marginleft`). Unknown elements will be ignored.

If a `ODT` file is supplied as a template, the drop-down box will be repopulated with the document's styles. Paragraphs with pre-existing styles will not be changed so it is best to supply the ODT before writing, or match the names of the styles in the `ODT` document to the default style names. The page format of `ODT` will override the page format parameters as well. 

It is possible to indicate a `nextstylename` element. Once this style is used, Plover2CAT will automatically switch to the next style when a new paragraph is created, so it is possible to alternate `Question` and `Answer` paragraphs.

Much more customization can be done using an `ODT` file as a template. Plover2CAT will append the transcript contents to the document, so if an `ODT` with a title page is supplied, the transcript contents will appear after the title page. 

Any style file (`JSON` or `ODF`) will be copied to the `styles` directory in order to keep the project self-contained.



### Style Settings

After making changes to the following controls, the `Modify Style` button has to be clicked to activate the change.

#### Text Properties

There is a dropdown box for font selection (based on installed system fonts). Font size can only be specified in integer format (it is not possible to supply something such as 12.5pt). 

Bold, italic, and underline buttons can be toggled. They can be used separately and in combination.

There are four different alignment buttons: left, center, right, and justified. Only one of the four buttons is able to be selected at one time.

Line spacing is measured as a % of line height. Single spacing would be 100%, and double spacing 200%.

`Average Char Width` is a read-only box. This displays the average width of a character in inches for the selected font. This is useful for setting characters per inch. However, actual characters per inch may vary if a proportional font is used (as characters will have varying width) compared to a monospace font (all characters have the same width).

#### Paragraph Properties

`First line indent` specifies how much the first line is indented compared to the rest of the paragraph.

`Tab Stop Distance` specifies the position of the tab stop if a tab appears in the text. If there is only one tab stop specified for the style, it will be editable. If there are multiple tab stops (such as when the style file is from ODF/RTF), it is not possible to edit tab stops within the editor. 

`Left Margin (Indent)` specifies the left margin of the paragraph. This is separate from the `left margin` of the page. It indents the entire paragraph relative to the `left margin` of the *page*.

`Right Margin (Indent)` is similar to the `Left Margin (Indent)`, but for the right.

`Top Margin` and `Bottom Margin` add space to the top and bottom of a paragragh, hence `(Padding)`. Microsoft Word calls this `Space before paragraph` and `space after paragraph`.

`Parent Style` is a drop down list containing all styles *except the current style*. The current style inherits formatting from the parent style, and will use those settings if nothing has been set for the current style. 

`Next Style` refers to the style to be set on the new paragraph following the current one. If a following paragraph already exists and has a style, the style will not be modified. One can for example set `Answer` as the style following `Question` and `Question` as the next style for `Answer`.

## Page Format

This is used for setting the page format used for export. The different fields should be self explanatory, controlling the different page margins and page dimensions. 

`Max char per line` sets the maximum characters allowed per line. 

`Max lines per page` sets the maximum number of text lines allowed per page. 

Both `max char per line` and `max lines per page` can have an `automatic value`. In this case, it is left to the editor to determine these values based on page parameters.

`Line numbering` can be checked or unchecked depending on need. The `frequency` refers to how often a line is numbered. Setting to `5` means every fifth line is numbered.

`Line timestamp` will add a timestamp to the beginning of the line. This value is based on the earliest chronological stroke time of the line. Depending on editing, timestamps across lines may not be in order if sections of text (and steno) were moved around.

This page format will apply to the entire document. The values are stored in the `config.config` file, along with other project attributes. 

If an `ODT` file is used to set styling, page format parameters are overridden. 

## Find and Replace

There are three kinds of find: text, steno, and untranslated, each with different options available. Searches can be forward or backward, and wrap around if selected.

Use `Ctrl+F` to move to the find and replace pane.

### Text Find

This will searching within translated text on the editor screen. Options for case sensitivity and whole word are available.

If any text in the editor is selected, it will automatically be put into the "Find" input box if `Ctrl+F` is used.

### Steno Find

This will search the within the underlying steno. The search text must match the stroke completely ("Whole Word/Stroke" option checked by default) such that `ST` will match `ST` but not `ST-T`. The search text must be valid steno ad there is no case-sensitivity.

### Untrans Find

This will search for any text that appears to be an untranslated steno stroke within the translated text. Only whole "words" in steno order and 3 or more letters long qualify as an untrans.

### Replace

If any of the three find methods has a match, it will be highlighted in the editor. The text in the "Replace" input box will replace the translated text. The underlying stroke data will not be changed.

### Replace All

This will search and replace all matches with the replacement text. This counts as one action, so undo will undo all replacements.

## Audio Recording

The audio will be saved automatically to the `audio` directory. A second attempt at recording will overwrite the existing file.

The options in the dropdown boxes will vary depending on the individual operating system.

- Input Device:  Choices will be any audio inputs available to the computer such as a microphone.
- Audio Codec: Windows systems like have PCM WAV at a minimum.
- File Container: A guess on the file format for the audio will be made based on the audio codec. If the codec is not one of the common ones, the audio file will not have a file extension, and users have to manually adding a file extension after recording is done.
- Sample Rate and Channels can be left on default, and the software will pick the best fit.
- Encoding Mode
  - Constant Quality: The recording will be done based on the quality slider, varying the bitrate to keep the same quality.
  - Constant Bitrate: The recording will use the same bitrate throughout, but quality of the recording will vary.

## Paragraph Properties Editor

The editor will automatically fill in paragraph properties such as when a paragraph is created, or the associated audio time. However, sometimes finer control is needed. 

By default, the properties are locked. Uncheck the `Lock` checkbox in order to edit `Creation Time`, `Audio Start Time` and `Audio End Time` and `Notes`. For what these properties mean and how they are created, see the [Editor](#the-editor) section. `Paragraph` and `Edit Time` are uneditable fields. Submit edits by pressing the `Edit Paragraph Properties` button. 

Any new steno input will cause the lock to be re-enabled (and editing disabled).

## Spellcheck

Spellcheck in the editor is powered by the [`spylls`](https://github.com/zverok/spylls) package. `Spylls` comes with the `en-US` dictionary from Hunspell for spellchecking. To use a different language dictionary, such as `en-GB`, download the desired dictionary extension from LibreOffice. LibreOffice packages all English dictionaries together as one `oxt` zip file ([link](https://extensions.libreoffice.org/en/extensions/show/english-dictionaries)). 

For Windows, after downloading, modify the file ending from `oxt` to `zip` to open. The files are paired together, one `*.dic` file with one `*.aff` file, both with the same file name. For `en-GB`, this will be `en_GB.dic` and `en_GB.aff`. Copy the `*.dic` and `*.aff` file into the `spellcheck` folder within the transcript folder. Then re-open the transcript and select the desired dictionary for spellcheck from the dropdown list.

# Formats

This section goes into detail on how these formats are implemented in the plugin. Most of the information is only relevant for development of the editor and making custom export formats based on the data.

## The Editor

The editor is a QTextEdit component. To most users, the only relevant aspect is that the text is organized into paragraphs, and data is stored on a per-paragraph basis.

There are several properties for each paragraph:

- Creation Time: this is the time that the paragraph is created. If it does not exist, the default is the time for the first stroke (see `steno data` below).
- Edit Time: this is the time of the last change to the paragraph. In the Paragraph Properties Editor, this property is not editable. the time will be modified each time there is a change to the paragraph and as a result, any manual edits will be overwritten.
- Audio Start Time: this is the time from the audio playing when the paragraph is created. This property can be edited, and should be used when trying to match timing, such as for captions.
- Audio End Time: this is the time when the audio has "passed on" from this paragraph. By default, if a paragraph does not have this property set, the audio end time for the paragraph is the audio start time of the subsequent paragraph. When `Stop Audio` is pressed, the time of the audio at the stop will be set as audio end time of the paragraph. Having one audio end time at the end of the transcript is important for making valid SRT caption files.
- Style: this is mostly useful for associating a paragraph style with the given block for exporting. See [styles](#styles) for the format and how to use.
- Notes: this is a text property for the user to make notes.

## Steno data

This section below describes in some detail QTextEdit and the data structures is used, which may not be so apparent in the code.

### `stroke` data

The most important property of each paragraph is the steno.

For each paragraph, there is a user data object (subclassing `defaultdict`) containing the base properties from above, and also holding the steno strokes (`strokes`) with corresponding text strings. The `strokes` entry is a list of lists, each element list having either three (or four) elements:
- time of stroke
- steno keys pressed
- text string
- audio time (optional)

An example of a list in `strokes` is:

```
["2001-01-01T01:23:45.678", "-T", "The"]
```

Two strokes in the paragraph will appear like this:

```
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"]
]
```

Notice the space before `cat`. This is a result of Plover with the `space before word` setting.

If the user strokes `-S`, Plover will output ` is` as the text. Then `strokes` will be updated to:

```
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"],
["2001-01-01T01:23:46.789", "S-", " is"]
]
```

If `*` is used, Plover will emit *three* backspaces (two spaces for `is` and one for the space at the front). Then `strokes` is updated back to: 

```
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"]
]
```

### Modifying on the `stroked` hook in Plover

Of the three engine hooks with data for `strokes`, `stroked`, `send_string` and `send_backspace`, the two `send_*` hooks will trigger before `stroked`. Therefore, `stroked` is used as the trigger to update the `strokes` data, as by then the number of backspaces and text string Plover emits for the stroke are available. If done the other way around, `send_string` will not know the present stroke, and the code becomes more complicated with the `strokes` data always a step behind. 

The `on_stroked` function in the code is the workhorse of the entire editor. It sets properties of the paragraph and modifies them before inserting the text Plover outputs, and also deleting text based on the number of backspaces Plover outputs.

### Lossy `stroke` data

Each time a stroke is written, Plover2CAT will first parse the the number of backspaces and/or text string the Plover engine outputs. The text string element (third) in the `strokes` sub-lists will be modified. The resulting `strokes` list will contain a *lossy* representation of the steno and the text as the backspaces Plover emits are used, but not recorded explicitly. 

Note the first example above where `is` is undone by `*` from the string `The cat is`. If another word is written (ie `The cat had` as `-T KAT H-`), there is no record of the stroke `S-` and `*` in the `strokes` data (though it will exist in the tape `-T KAT S- * H-`, making the tape the definitive and most accurate record on what was written). `S-` and `*` are not necessary to form the text string and are "dropped" in a sense.

Take for example writing `pleasing`.

```
strokes = [
["2001-01-01T01:23:45.678", "PHRES", "please"]
]
```

When `-G` is stroke, for the suffix `-ing`, Plover will emit one backspace (to remove the `e`), and the text string `ing`. The stroke representation will become:

```
strokes = [
["2001-01-01T01:23:45.678", "PHRES", "pleas"],
["2001-01-01T01:24:56.789", "-G", "ing"]
]
```
One benefit of doing this is that the user can still search the steno for the stroke `PHRES` and find `pleasing`. 

## Actions

Writing/removal of steno has been implemented using custom `QUndoCommand` classes. They are `steno_insert`, `steno_remove`, `split_steno_par` and `merge_steno_par`. The former two commands simply insert/remove text and associated steno from the `stroke` data.

### Merging and splitting paragraphs

With the QPlainTextEdit, when a paragraph is deleted, so is the data associated with it. But when the QT undo is used to restore the deleted paragraph, the data is still gone. This creates problems when a user merges paragraphs (by backspacing) or creates a new paragraph in the middle (pressing `enter`), common operations in a word processor. If two paragraphs are merged, the steno data stored in the second paragraph will disappear, and the first paragraph will have text from two different paragraphs, but the steno will only be of the first paragraph. Because of this limitation, there are two commands `split_steno_par` and `merge_steno_par` to be used when merging/splitting paragraphs. This way, the underlying steno will be merged and set properly rather than being lost.

For example, a merge should be like placing the cursor at the beginning of the paragraph and then pressing backspace:

```
# Paragraph one text: The cat\n
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"],
["2001-01-01T01:23:47.890", "R-R", "\n"]
]
```

with

```
# Paragraph two text: please\n
strokes = [
["2001-01-01T01:24:56.789", "PHRES", "Please"],
["2001-01-01T01:24:67.890", "R-R", "\n"]
]
```
should create something like:

```
# Paragraph one text: The cat Please\n
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"],
["2001-01-01T01:24:56.789", "PHRES", " Please"],
["2001-01-01T01:24:67.890", "R-R", "\n"]
]
```

When the cursor is at the end of the document, stroke data is appended to the end. When the cursor is in the middle of text, a cut and paste action is used to mimic the writing. When backspacing across paragraphs, the editor calculates and using as many cut actions as needed together with the merge paragraph action. Similarly, when the writing contains new lines, the split paragraph action is used together with paste to create new paragraphs in the middle of text without erasing steno data from later paragraphs that are already written.

### Steno across paragraphs

Sometimes, a stroke will have a translation that includes newlines `\n`. In cases like this, Plover2CAT will break up the string based on the `\n` into separate insertions. So `Line one\ntwo\nthree` will be three separate calls to `steno_insert`, with a call to `split_steno_par` between to generate a new paragraph. This is treated as one action for undo/redo even though there are actually five separate actions. It is not possible to undo in the middle.

The opposite of strings with newlines are `*` commands for Plover undo that crosses paragraph. This might be the result of the previous stroke containing new lines or in editing where the number of backspaces is greater than the number of characters in the paragraph. Plover2CAT calculates the position reached by the number of backspaces. Each time, `steno_remove` is used to remove as much text as possible until the cursor reaches the beginning of the paragraph, followed by a `merge_steno_par` call to merge the paragraphs, repeating until the number of backspaces is reached. This will also be treated as one action for undo/redo.

## Configuration File

The configuration JSON file contains transcript level settings. It is also the file selected in order to open a previously saved transcript. When a new transcript is created, the file is automatically generated. The file is placed in the root directory, with keys for page margins, space placement, style file used for ODT export, and a list of the dictionaries to be loaded when the transcript is opened.

## Transcript Dictionaries

After a new transcript is created, a default dictionary in JSON format is put into the `dict/` folder. The same dictionary is also loaded into Plover on the top. The dictionary contains entries for common shortcuts such as Copy `Ctrl+C`. These strokes use the `-FRLG` chord on the right hand and the finger-spelling chords for the left hand. So `Ctrl+C` is `KR-FRLG`. Shortcuts using `Ctrl+Shift` such as for "Slow down audio playing" uses `S-FRLGS`. 

When a new dictionary is added through `Add Dict`, the dictionary file is copied into the `dict/` folder.When a dictionary is removed with the `Remove Transcript Dictionary`, the dictionary file is not deleted from the folder, just not loaded into Plover.

## Transcript data

The `transcript-YYYY-MM-DDTHHMMSS.transcript` contains the editor data. The data on the document is saved in JSON, the paragraph number being the name corresponding to an object of the visible text and all properties for that paragraph. The JSON is minified, so use an online JSON beautify tool if needed.

## Tape

The tape file `transcript-YYYY-MM-DDTHHMMSS.tape` tracks the user strokes. This file is saved at every stroke.

There are four fields separated by the `|` character:

- Time of stroke
- Audio time (if available)
- Position of cursor as (paragraph, position in paragraph)
- Steno keys pressed

This should make for easy parsing for other uses.

## Style

The `default.json` file looks like

```
default_styles = {
    "Normal": {
        "family": "paragraph",
        "nextstylename": "Normal",
        "textproperties": {
            "fontfamily": "Courier New",
            "fontname": "'Courier New'",
            "fontsize": "12pt"
        },
        "paragraphproperties": {
            "linespacing": "200%"
        }
    },
    "Question": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Answer",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Answer": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Question",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Colloquy": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",  
        "paragraphproperties": {
            "textindent": "1.5in"
        }     
    },
    "Quote": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal", 
        "paragraphproperties": {
            "marginleft": "1in",
            "textindent": "0.5in"
        } 
    },
    "Parenthetical": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",
        "paragraphproperties": {
            "marginleft": "1.5in"
        }     
    }
}
```

These parameters attempt to recreate the NCRA's [transcript format guidelines](https://www.ncra.org/About/Transcript-Format-Guidelines).


Plover2CAT uses the Open Document Format names for paragraph and text properties, and also uses style inheritance in a similar manner. If a property such as `linespacing` is not set (in the case of the `Question` style above), if the parent style has the setting (`Normal` has `linespacing` of `200%`), then the current style `inherits` that setting (`Question` style will also have `linespacing 200%`). If a style has a property set, and so does the parent style, the current style's property value overrides the parent style's value.

This means that when creating a style file by hand, there should be at least one base style that other styles inherit from. It also means that styles should not have themselves set as their own parent style as that causes a loop.

This is the complete list of attributes that can be set in Plover2CAT, with comments explaining possible values. This is based on the Open Document Format spec which contains even more details.

```

{
    "Name": { # name of the style
        "family": "paragraph",  # set to "paragraph"
        "defaultoutlinelevel": "", # heading level, 1-10, ordinary text has no level
        "parentstylename": "", # name of style the current style inherits properties from
        "nextstylename": "", # name of style for new paragraph after this one
        "paragraphproperties": {
            "textalign": "left/center/right/aligned", # has to be one of these four choices
            "textindent": "", # first line indent distance in inches ie "1in"
            "marginleft": "", # paragraph left margin in inches
            "marginright":"", # paragraph right margin in inches
            "margintop": "", # paragraph top margin in inches
            "marginbottom": "", # paragraph bottom margin in inches
            "linespacing": "" # line spacing using %, ie 200% for double space
            "tabstop": "" # can be one value ("2.0in") or a list for values ["1.0in", "1.5in", "2.0in"] for tabstops
        }
        "textproperties": {
            "fontname": "", # name of font
            "fontfamily": "", # font family
            "fontsize": "", # integer value for font size in pt, ie "12pt"
            "fontweight": "none/bold", # the style may not have "fontweight", but if it does, it has to be set as "bold"
            "fontstyle": "none/normal/italic", # the style may not have "fontsize" or set as "normal" or "italic"
            "textunderlinetype": "none/single", # the style may not have "textunderlinetyle" or it has to be set as "single"
            "textunderlinestyle": "none/solid" # the style may not have "textunderstyle" or it has to be set as "solid", but only if "textunderlinetype" is set
        }
    }
}


```

## Autocomplete Wordlist

Autocomplete can be toggled on and off. A `wordlist.json` file in a `sources` directory within the transcript directory is needed containing prospective suggestions. This has to be a JSON with the format `suggestion` : `steno`. Spaces are allowed in `suggestion`, but all whitespace (tabs and new lines) will be replaced by spaces.

An example is:
```
{
	"doctor": "TKR",
	"England": "EPBG/HRAPBD",
	"English": "EPBG/HREURB",
	"Europe": "AO*URP",
	"French": "TPREFRPB",
	"God": "TKPO*D"

}

```

## Supported RTF Import

Import of RTF/CRE transcript files produced by other CAT software is not fully supported.

`pyparsing` is used to import RTF/CRE files. Only a subset of the RTF/CRE spec is supported.

Recognized RTF flags

    Default font (\deffont)
    Paper height (\paperh)
    Paper width (\paperw)
    Top margin (\margt)
    Bottom margin (\margb)
    Left margin (\margl)
    Right margin (\margr)
    New paragraph (\par)
    Stylesheet (\stylesheet)
    Style (\s)
    Next Style (\snext)
    Parent Style (\sbasedon)
    Style margins (\li \ri \fi \sb \sa)
    Text alignment (\ql \qr \qj \qc)
    Tabstops (\tx)
    Font table (\fonttbl)
    Font family (\froman \fswiss \fmodern \fscript \fdecor)
    Font (\f)
    Font size (\fs)
    Bold and italic (\b \i)
    Underline (\ul) (Only single solid line)
    Creation time (\creatim \yr \mo \dy)

Recognized RTF/CRE flags

    Timecode (\cxt)
    Steno (\cxs)
    Frame rate per second (\cxframes)
    Automatic Text (\cxa)


The styles from the original RTF can be re-used as templates for transcripts.

1. Open the RTF/CRE file in LibreOffice or Microsoft Word, check if desired styles are recognized in the word processor (they may appear as custom styles).
2. Make sure parent styles and next style for each style are set as desired (next style of Q might be Contin Q) through the style editor. Depending on word processor, some formatting may not be imported properly.
3. Delete all textual content/headers/footers if not desired.
4. Save the file as an ODT file. 
5. Load into Plover2CAT by selecting it as a style source file in the Styling pane before exporting to ODT.


## Export Formats Overview

Similar to the editor description, this section may go into detail not necessary for most users depending on the format. The table below summarizes what features are available for each export format.

+-------------+----------+---------+-----------+---------+---------------+-----------+------------+
| Format      | Richtext | Line \# | Timestamp | Page \# | Header/Footer | Char/Line | Lines/Page |
+=============+==========+=========+===========+=========+===============+===========+============+
| Plain Text  | No       | No      | No        | No      | No            | No        | No         |
+-------------+----------+---------+-----------+---------+---------------+-----------+------------+
| Basic ASCII | No       | ✓       | No        | ✓       | No            | No        | No         |
+-------------+----------+---------+-----------+---------+---------------+-----------+------------+
| ASCII       | ✓\*      | ✓       | ✓         | *No*    | *No*          | ✓         | ✓          |
+-------------+----------+---------+-----------+---------+---------------+-----------+------------+
| HTML        | ✓\*      | ✓       | ✓         | *No*    | *No*          | ✓         | ✓          |
+-------------+----------+---------+-----------+---------+---------------+-----------+------------+
| ODT         | ✓        | ✓       | ✓         | *No*    | *No*          | *No*      | *No*       |
+-------------+----------+---------+-----------+---------+---------------+-----------+------------+
| *RTF/CRE*   |          |         |           |         |               |           |            |
+-------------+----------+---------+-----------+---------+---------------+-----------+------------+

\* No font support, indents and other layout is converted to closest approximation using spaces for padding.

Italics for features not yet supported but planned.

### Plain Text

The plain text format contains just pure text, without any property information. This format does not require any properties in paragraphs. Each paragraph becomes one line in the text document.

### Basic ASCII

This is the ASCII format as specified in Ipos Eclipse. Page numbers begin on column 1, and are padded to 4 places. Each line of the text begins with line numbers starting on column 2, with text beginning on column 7 and is < 78 characters in length. Hard-coded into the code at this time is 25 lines per page. This export format will ignore style formatting.


### ASCII

This is an ASCII format with support for line numbers and timestamps, using the style formatting.

Not all formatting can exported to all formats. For example, text files cannot have multiple fonts or different font sizes. Plover2CAT will do its best to emulate formatting for ASCII files. For example, line spacing settings will be rounded, so line spacing of 150% would become a line of text and an empty line (like double space). Tabstops, paragragh left and right margins, indents are all converted from inches to spaces (using 10 spaces per inch). Top and bottom padding for paragraphs are converted from inches to empty lines (using 6 lines per inch). As a result, the text file contains a best-effort attempt to mimic formatting using text and spaces.

### SubRip

Plover2CAT implements the simple SubRip (`*.srt`) captioning file format for exporting. This format requires all paragraphs to have an Audio Start Time property. The last paragraph for the audio needs an Audio End Time property, which can be set manually or by pressing `Stop` and having the time automatically be set for the paragraph. 

### OpenDocument Text

The Open Document Format (`ODF`) is an open source standard for documents based on XML. An OpenDocument text file (`*.odt`) is assumed to be the main export format for users who want formatted documents directly from Plover2CAT. Rather than creating a word processor with comprehensive formatting options within Plover2CAT, using a fully functional word processor such as `LibreOffice` is more flexible and efficient, since `LibreOffice` or `Microsoft Office` will have properly implemented and documented user interfaces.

A user can write the transcript in Plover2CAT, do some simple editing and formatting, and then export to a word processor to do as much paragraph/character formatting as needed. 

# Development

Plover2CAT at present, is one gigantic class, and with absolutely no tests.

## Steno-Annotated ODF

Plover2CAT should produce an annotated document, putting raw steno in the `ruby` element to annotate the corresponding words. This takes advantage of the annotations which are originally for Asian language pronunciation.

## RTF/CRE

RTF/CRE appears to be the common exchange format for CAT software.

The specs are on the [internet archive](https://web.archive.org/web/20201017075356/http://www.legalxml.org/workgroups/substantive/transcripts/cre-spec.htm)

RTF import has been implemented selectively. Next step should be RTF export.

More RTF example files from different companies are needed to test import capabilities as different cat software have their own own flags.

## Richtext Features

While richtext editing has been enabled, some common features of word processors and professional CAT software are missing. Primary ones are 1) embedding images, 2) table of contents/index and 3) tables.

QTextEdit is able to work with images out of the box (just need to implement certain features in code for exporting, and also folders for saving image data.)

Indexes (in reality, a table of contents) for ODF depends on having "heading" styles. This can be integrated. RTF table of contents is possible (based on the spec). The difficulty will be keeping track of the text in the editor selected for table of contents if there is custom text. 

Tables are likely more difficult to implement and may require an editor widget

## Header/Footer

This should use JSON to implement in its own folder. ODF has support for both, so does RTF. UI controls have to be created, and an option for first page special.

## Alternative formats

HTML: The present HTML format is just the ASCII text in a code block wrappd up with html tags. HTML can be much more flexible (ie table of contents, search, images, embedded audio etc), even if the plain text structure has to be kept.
Latex: suggested
Epub?

## Customizable shortcuts

Shortcuts are hardcoded, but user specifying shortcuts may be possible. (see qkeysequenceedit). This is more in case hardcoded key sequences are in conflict with other user shortcuts, not that shortcuts are difficult to use (since the keys are emitted by plover and the outline can be set to anything).

## Preview of search and replace

Search and replace is done "blindly" in the case of replace all, and also more timeconsuming if done one by one. A preview might allow for a quick check, summarizing the number and showing the context.

## Autocomplete enhancement

Right now, autocomplete suggestions come from a pre-set list. The engine should update in near-realtime and take suggestions from the present text, or other transcript json/rtf.