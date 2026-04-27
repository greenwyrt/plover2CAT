# Development

plover2CAT's development is built on top of the Qt Framework and the Plover engine hooks. The various pages discuss certain challenges and reasons for why plover2CAT has developed in certain directions.

```{toctree}
:maxdepth: 1
Challenges of a steno-aware editor <stenoeditor.md>
Lossy steno data <lossysteno.md>
Plover engine hooks <enginehooks.md>
Transcript data formats <transcriptdata.md>
```

The sections below list things that could be part of future versions. They are not listed in order of priority.


## Comments/Track Changes

See `<office:annotation>` and `<office:annotation-end>` in the ODF spec for comments.

Might be implemented as functional length 1 elements. Separate dialog pane to show all comments, move cursor to location if clicked.

`<office:annotation>` has creator, date, and unique id in `office:name`.

`<text:tracked-changes>` is used in ODF spec for tracked changes.


## Simultaneous editing and writing

Right now, steno insertion is based on the cursor position unless it is locked at end. It is not possible to edit with a normal keyboard the same time a steno machine is writing. 

Proposed solution: replace `engine._keyboard_emulation` on startup with your own subclass of `plover.output.Output` and implement send_backspaces, send_string, and send_key_combination as needed, at least until new version of Plover with output plugins.

Status: somewhat implemented, as `output` subclass works with `tape_translate`, but input/output selection/always at end options need to be thought out
Drawback: cannot write in any other windows

## Optimizing `get_suggestions`

For both tapey-tape and clippy, the file is read from the start repeatedly. It may be better to store lines in memory and only ingest new lines (keep track of position with tell and then seek). The drawback is increased memory. Also, there are repeated lookups with Plover's engine, which may also be reduced with a local dict.

Alternatively, set up separate threads to digest and report back the counter dict

## Parsable action logging

The log messages are not formatted consistently or easy to decipher.

Then one could reconstruct transcript from logs.

## Task manager

Hook into either the action logs to replay

## RTF/CRE

RTF import/export has been implemented selectively. 

More RTF example files from different companies are needed to test import capabilities as different CAT software have their own own flags.

## Autocomplete enhancement

Right now, autocomplete suggestions come from a pre-set list. The engine should update in near-realtime and take suggestions from the present text, or other transcript json/rtf. However, there could be performance considerations if this is a large transcript. Engine input processing may need to be offloaded to a separate thread on regular intervals or initialized by the user (ie, when user knows that there is time to update) or both.

Occurrences of words can be counted with a `Counter`, and the first occurrence can be searched for steno in the blocks.

Autocomplete and next word prediction are not the same things.

## Enhancing search types

Possible new search types: 
- time of stroke, or time of paragraph
- exact, starts with, ends with, contains, partial stroke
- filters for # of strokes, includes numbers/punctuation etc 

## Alternative formats

HTML: The present HTML format is just the ASCII text in a code block wrappd up with html tags. HTML can be much more flexible (ie table of contents, search, images, embedded audio etc), even if the plain text structure has to be kept.

Latex: suggested

Epub: More of a reading format

Steno-Annotated ODF: Plover2CAT should produce an annotated document, putting raw steno in the `ruby` element to annotate the corresponding words. This takes advantage of the annotations which are originally for Asian language pronunciation.

## Style highlighting

Paragraphs with certain styles could get a highlight color, would conflict with element styling (ie two font colors).
Solution: QColors can be blended by addition.

## Richtext Features for indexes and tables

While richtext editing has been enabled, some common features of word processors and professional CAT software are missing. Primary ones are 1) embedding images (implemented), 2) table of contents/index and 3) tables.

Tables are likely more difficult to implement and may require an editor widget.

## Editor speed

At present, when loading a transcript, the main bottleneck in speed comes from rendering paragraph styles for display and setting page format on the document. Populating the editor with text is incredibly fast by avoiding the use of `QUndoCommands`. With styles, there is the collapsing of the style dict, the setting of formats and the checking of each text element in case any are images slow down the processes.

The other processes that scan the whole document again and again are fields (on every update), and index entries, and the edits that have to be made depending on how frequently the element occur.

Data retrieval and storage are likely as fast for the limitations, considering that text and steno data have to be linked, and custom data storage for paragraphs would mean cleanup of data that Qt does automatically. If loading from file, the original dict is kept in memory. Blocks that are modified are marked using `userState`. For saving, each paragraph's state is checked, and at the first block with `userState`, all subsequent paragraphs get data extracted and stored. 

Docks now do not update unless they are open and visible. Closing all docks could be set as a "writing mode" with all docks hidden vs editing mode with docks set visible.

## Editor memory

While it has not yet occurred, it is very likely that at some time, memory could pose a big problem with very big transcripts, or just multiple transcripts open. A memory saving strategy would be to use slots for element objects.

## `userState` in editor

An enum class have been created for `userState`. Right now, only `CHANGE` is being used for saving.

- [ ] use new enum to set paragraph to read-only while still navigable by cursor
    - possibly using cursor to move forward and back blocks
    - some actions, such as normal copy should work, others like copy/cut should not
    - color paragraph with qbrush for texture
- [ ] state should be updated before being saved into transcript data, and then converted when imported
- [ ] tests for saving
    - [ ] set transcript_data and textEdit are different, make sure everything after userState changed is saved
    - [ ] toggle first paragraph


## Transcript JSON format

An alternative to the regular JSON format would be using JSONL, with each line per paragraph. This would facilitate reading subsets of a file, and reducing memory when loading a transcript. 

Also, rather than keeping the backup document in memory, re-read the saved file until the first par with changed state, saving each line to new file, and then writing the new data before replacing old saved file with new one.


## Ongoing

### Unit tests 

*In progress*

Tests should run from a dialog in editor using `unittest`. See this [link](https://stackoverflow.com/questions/20433333/can-python-unittest-return-the-single-tests-result-code) for returning a `TestResult`. Output should be redirected by specifying the `stream` argument for a `StringIO`.

### Docstrings 

Functions and class methods should be fully documented. 

`PloverCATWindow` should accept arguments for methods that need dialog input. Modification should be handed off to `TextEditor` 

### Slots

PySide6 decorators improve memory/performance


## Possible improvements list

- [ ] writing aids
    - languagetool (https://pypi.org/project/language_tool_python/)
        - returns JSON format
        - need to retrieve response and format into something to apply
        - ~200mb installation?
    - thesaurus (libreoffice: MyThes)

- [ ] dialogs should move to own folder (too many)

- [ ] toolbox tabs should be refactored out if possible (TTS, paragraph, steno search)

- [ ] find all not working with wrap, does seem to find above

- [ ] stroke count (status bar/dock window)

- [ ] edit window title along with tab title

- [ ] standardize log debug and info messages with statusbar messages
    - info messages should also be json parsable

- [ ] user preferences file
    - [ ] switch from saving directly in system settings
    - [ ] can import initially
    - [ ] end goal: multiple profiles for same computer
    - [ ] some `QSettings` should remain so, others into user profile

- [ ] add to reveal steno view
    - version with show strokes
    - link to cursor

- [ ] media controls do not collapse well, should be using flowLayout to move duration and track to new

- [ ] page breaks for text and odf export formats
    - unicode ↡ is used for line feed
    - for odf
        - needs `<office:text text:use-soft-page-breaks="true">` in the body
        - odf uses fo-break-before/fo-break after with a custom style for line before/after the page break
    - for text
        - need as many new lines as possible before/after paragraph
        - within `format_text`, do regex for ↡, and check if it is page-break element
        - create empty \n lines as needed
    - for rtf, insert \page command
    - for srt, remove page-break element
    - conditional page break

- [ ] tape dialog improvements:
    - render translated strokes unselectable
    - the undo should re-enable undone stroke

- [ ] phonetic system for CART
- [ ] hot key mode
- need QAudioProbe equivalent
    - [ ] pause audio when stop writing for amount of time
    - [ ] during playback, skip silence (or threshold)
- [ ] have cursor follow playback
- [ ] merge/split tests with new style
- [ ] do "reset" of paragraphs based on block_stroke data, edit using SequenceMatcher (not plausible to use for all edits?)
- [ ] find all display navigation will not be correct if document modified, but also cannot use isClean of undo stack to track changes
- [ ] change `__getitem__(key)` behaviour in `element_collection` to return the element, not `element_collection` instance, mimics default behaviour of list
- [ ] a/an search
- [ ] replace punctuation as needed, include "--" and "..."
- [ ] diff compare versions
- [ ] downgrade element, use `el.__class__.__mro__[1]()` which returns new instance, construct element from dict, only do if `el.__class__.__name__` is not "text_element"
- [ ] other things to add to insert menu, checkable for export in supported format (table of contents, table of figures/exhibits), number ranges for autonumbering, special characters (more dialog)
- [ ] different time code formats
- [ ] control line numbering position
- [ ] control timestamp position
- [ ] switch between plain text and wysiwyg editors
- [ ] custom scripts for keyboard editing shortcuts



# Build and bundle docs

```
source ~/plover2CAT/.venv/bin/activate
cd docs
make qthelp
/usr/lib/qt6/libexec/qhelpgenerator _build/qthelp/plover2CAT.qhp
/usr/lib/qt6/libexec/qhelpgenerator _build/qthelp/plover2CAT.qhcp
cp _build/qthelp/plover2CAT.qch ../plover_cat/data
cp _build/qthelp/plover2CAT.qhc ../plover_cat/data
```