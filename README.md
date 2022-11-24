Plover2CAT is a plugin for Plover, the open-source stenography engine. If the only user requirement is to write steno on the computer, this plugin is not needed as Plover is more than sufficient. Plover2CAT provides some of the features a computer-aided-transcription (CAT) program has to produce a transcript for captioning or other purposes. 

# Features Overview:

- [x] a plain text editor with steno hidden underneath
- [x] timestamps for each stroke and associated with each piece of text
- [x] conventional editing features such as cut/copy/paste while keeping steno data attached
- [x] undo/redo history
- [x] automatic creation and loading of transcript-specific dictionaries for each transcript
- [x] find and replace for simple text, steno stroke, and untrans.
- [x] retroactive define, and define last translate with replacement of all previous occurrences and new outline sent to transcript dictionary
- [x] an audiovisual player, with controls for timing offset, playback rate, skipping forward and back
- [x] synchronization of steno with the audio/video file for transcription
- [x] audio recording synchronized with steno (file format dependent on codecs in operating system)
- [x] export transcript to plain text, Eclipse ASCII, SubRip, and Open Text Document formats (with style templates)
- [x] saves paper tape with keys pressed, position of cursor in document, and timestamps at each stroke
- [x] suggestions based on stroke history (powered by Tapey Tape), updated every paragraph
- [x] spellcheck using the `spylls` library, ability to select spellcheck dictionaries 
- [x] versioning using the `dulwich` library, switch between previously saved transcript states.
- [x] basic import of RTF/CRE transcript

This plugin is built on Plover and inspired by [plover_cat](https://github.com/LukeSilva/plover_cat). 


# Installation

Open the terminal following instructions here [on the command-line](https://github.com/openstenoproject/plover/wiki/Invoke-Plover-from-the-command-line). On Windows, paste in:

```
 .\plover_console.exe -s plover_plugins install git+https://github.com/greenwyrt/plover2CAT.git
```

On MacOS and Unix systems, use `plover` rather than `plover_console.exe`.

# Getting Started

## Starting a New Transcript

Open Plover2CAT from within Plover after installation, by Tools --> Plover2CAT. A window with a main editor, and dockable containers for suggestions, paper tape, and other functions will appear. Create a new transcript with File --> New (or `Ctrl + N`). A folder selection dialog will appear. Plover2CAT will create a transcript folder with a timestamp at the selected location.

Once Plover is enabled, writing to the main editor will be possible. The main function of Plover2CAT is for writing steno, and by default, only steno translated by Plover will be written (and deleted with the `*`). 

A custom dictionary for the transcript is loaded into Plover, prepopulated with shortcuts for common actions. When File --> Close is used to close the transcript, the custom dictionary will be removed from Plover.

## Default CAT behaviour

Check "Lock Cursor at End" and "Capture All Steno Input" to only write to end of document and to still write even when editor window is not in focus. By default, writing is inserted into any part of text, and only when window is in focus.

## Opening Audiovisual Files

Select an audio file on the computer by Audio --> Open Audio (`Ctrl + Shift + O`). When audio is playing, steno strokes will be timestamped with the audio time. Open the "Paragraph Properties Editor" in the Toolbox pane to see the timestamps associated with each paragraph.

## Recording Audio

Open "Audio Recording" in the Toolbox Pane to select parameters for recording such as the input device. Click Record/Pause on the toolbar or through Audiovisual --> Record/Pause to start recording. Use Audiovisual --> Stop Recording to stop recording. 

## Saving and Export

The transcript will be saved as an JSON file within the created transcript folder when File --> Save (`Ctrl + S`) is used.

The available export formats are:
  - Open Document Text
  - SubRip
  - ASCII
  - Plain Text

For more details on each format and the different requirements, see the User Manual. 

## Close Transcript

Use File --> Close to close the transcript and File --> Quit (`Ctrl+Q`) to quit the editor, with optional check to save if changes have been made. **DO NOT** use the `Alt+ F4` as that causes an instant exit without saving.


# Acknowledgements

This plugin is under the MIT license.

Plover and PyQt are both under the GPL license. 

Fugue icons are by Yusuke Kamiyamane, under the Creative Commons Attribution 3.0 License.

# Development


Plover2CAT at present, is one gigantic class, and with absolutely no tests. See the user manual for details of formats such as stroke data, and wished-for features.



