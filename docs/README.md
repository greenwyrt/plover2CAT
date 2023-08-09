# Documentation

To get started, go through the following tutorials that will go through installing, writing into the editor, adding formatting, and exporting the transcript.

## Get Started

Start with #3 if you already have Plover installed and know how to install Plover2CAT from the command line.

1. [Install Plover](tutorials/install-plover.md)
2. [Install Plover2CAT as a Plover plugin](tutorials/install-plover2cat.md)
3. [Create new transcript in Plover2CAT](tutorials/create-transcript.md)
4. [Write in the Plover2CAT editor](tutorials/writing-editor.md)
5. [Export to text and Open Document Format](tutorials/export-file.md)

## How To ____

Much of the following content is more useful if the Plover2CAT editor is open and there is already an existing transcript in the editor to visualize effects. The user should know what stenography is at this point, and can set up a machine / keyboard for writing through Plover.

### Perform common CAT functions

- [Write only to end of document](howto/lockcursor.md)
- [Write even when window is not in focus](howto/captureoutput.md)
- [Merge paragraphs](howto/mergepar.md)
- [Split a paragraph](howto/splitpar.md)
- [Add automatic paragraph affixes](howto/auto_affixes.md)
- [Retroactive Define for selection in editor](howto/retrodefine.md)
- [Scan for last untranslated and add outline to dictionary/delete](howto/definelast.md)
- [Define and insert a user field](howto/userfield.md)
- [Insert index entries](howto/indices.md)
- [Navigate to paper tape and back](howto/tapelinking.md)
- [Generate dictionary suggestions from transcript](howto/transcriptsuggest.md)
- [Import RTF/CRE transcript file](howto/importrtf.md)
- [Enable autocompletion and add terms](howto/autocompletion.md)
- [Translate tape files](howto/translatetape.md)
- [Set up and display captions](howto/captions.md)

### Configure the editor

- [Organize, show, and hide docks](howto/dockmanagement.md)
- [Organize, show, and hide toolbars](howto/toolbarmanagement.md)
- [Set window font](howto/windowfont.md)
- [Set background color](howto/backgroundcolor.md)
- [Set paper tape font](howto/papertapefont.md)
- [Show invisible characters](howto/showall.md)
- [Move cursor](howto/cursormove.md)
- [Set custom shortcuts for menu items](howto/setcustomshortcuts.md)
- [Set autosave](howto/autosave.md)

### Do common editing tasks

- [Find/Replace](howto/findreplace.md)
- [Undo and redo](howto/undoredo.md)
- [Cut/Copy/Paste/Normal Copy](howto/copypaste.md)
- [Insert normal text](howto/insertnorm.md)
- [Insert images](howto/insertimages.md)
- [Deleting text](howto/deletetext.md)
- [Spellcheck](howto/spellcheck.md)
- [Add extra language dictionaries](howto/addspelldict.md)
- Reset paragraph
- [Revert to previously saved version](howto/revert.md)
- [Navigate with headings](howto/navigate.md)

### Play and Record Audiovisual files

- [Select media file to play](howto/selectmedia.md)
- [Play, pause and stop](howto/playpause.md)
- [Set playback rate](howto/playbackrate.md)
- [Set up a time offset for syncing with writing](howto/audiosync.md)
- [Skip forward and back](howto/audioseeking.md)
- [Show/hide video](howto/videotoggle.md)
- [Set up and start audio recording](howto/audiorecording.md)

### Set and modify styles for paragraphs

- [Apply style to paragraph](howto/applystyle.md)
- [Modifying existing style](howto/modstyle.md)
- [Create a new style](howto/newstyle.md)
- [Select a style file other than the default](howto/selectstylefile.md)
- [Generate styles from template](howto/generatestyletemplate.md)

### Manage transcript dictionaries

- [Add custom dictionary](howto/adddict.md)
- [Remove a transcript dictionary](howto/removedict.md)

### Set and modify page layout properties

- [Set page size and margins](howto/pagesetup.md)
- [Create headers and footers for export](howto/headerfooter.md)
- [Set max characters per line and max lines per page](howto/maxlinemaxchar.md)
- [Enable line numbering and timestamps](howto/linenumtimestamp.md)

## Reference

- [Window Layout](reference/editorlayout.md)
- [Menu](reference/menu.md)
- [Docks](reference/docks.md)
- [Transcript folder structure](reference/folderstructure.md)
- [Data formats](reference/dataformat.md)
- [Export formats](reference/export.md)
- [Supported RTF/CRE features](reference/rtf_support.md)
- [Commands](reference/commands.md)


In development:
- [Editor class](reference/main.md)
- [Custom text objects](reference/elements.md)
- [Dialogs](reference/dialogs.md)

## Discussions of design, development, and descriptions

- [Challenges of a steno-aware editor](discussion/stenoeditor.md)
- [Lossy steno data](discussion/lossysteno.md)
- [Plover engine hooks](discussion/enginehooks.md)
- [Transcript data formats](discussion/transcriptdata.md)
- [Future development goals](discussion/development.md)

## Getting help

Two ways: 1) Send a message over Discord. I am plants#4820 or 2) Open an issue on Github.

Helpful things to do: 
- Go to **Help > About** to view the version number.
- Compress and attach the entire transcript directory, or the `*.tape` and `*.transcript` files. 
- If possible, add steps to reproduce the problem. 
- Add the log output from running Plover (debug) after an attempt to cause the exact same error.

