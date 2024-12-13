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

## Possible improvements

- [ ] find all display navigation will not be correct if document modified, but also cannot use isClean of undo stack to track changes
- [ ] sequentially process tape to translation
- [ ] rename audiovisual to media in UI and beyond
- [ ] apply same style to multiple paragraphs (cursor highlighting multiple paragraphs)
- [ ] change `__getitem__(key)` behaviour in `element_collection` to return the element, not `element_collection` instance, mimics default behaviour of list
- [ ] a/an search
- [ ] replace punctuation as needed, include "--" and "..."
- [ ] diff compare versions
- [ ] do "reset" of paragraphs based on block_stroke data, edit using SequenceMatcher (not plausible to use for all edits?)
- [ ] downgrade element, use el.__class__.__mro__[1]() which returns new instance, construct element from dict, only do if el.__class__.__name__ is not "text_element"
- [ ] other things to add to insert menu, checkable for export in supported format (table of contents, table of figures/exhibits), number ranges for autonumbering, special characters (more dialog)
- [ ] text to speech
- [ ] different time code formats
- [ ] control line numbering position
- [ ] control timestamp position
- [ ] switch between plain text and wysiwyg editors
- [ ] custom scripts for keyboard editing shortcuts

## Simultaneous editing and writing

Right now, steno insertion is based on the cursor position unless it is locked at end. It is not possible to edit with a normal keyboard the same time a steno machine is writing. 

Proposed solution: replace `engine._keyboard_emulation` on startup with your own subclass of `plover.output.Output` and implement send_backspaces, send_string, and send_key_combination as needed, at least until new version of Plover with output plugins

## Element styling

Color styling for different elements such as text vs index entry. This will require changing `QTextCharFormats` by setting Foreground. It may also impact editor speed depending on implementation.

## Parsable action logging

The log messages are not formatted consistently or easy to decipher.

Then one could reconstruct transcript from logs.

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

## Preview of search and replace

Search and replace is done "blindly" in the case of replace all, and also more timeconsuming if done one by one. A preview might allow for a quick check, summarizing the number and showing the context.

## Style highlighting

Paragraphs with certain styles could get a highlight color, would conflict with element styling (ie two font colors)


## Richtext Features for indexes and tables

While richtext editing has been enabled, some common features of word processors and professional CAT software are missing. Primary ones are 1) embedding images (implemented), 2) table of contents/index and 3) tables.

Tables are likely more difficult to implement and may require an editor widget.

## Refactoring editor

*in-progress for ver 3*

The editor should be refactor into a smaller class.

Methods that exclusively work on the `QTextEdit` could possibly be extracted and refactored from the `PloverCATWindow` into the `PloverCATEditor` custom class.

## Editor speed

At present, when loading a transcript, the main bottleneck in speed comes from rendering paragraph styles for display and setting page format on the document. Populating the editor with text is incredibly fast by avoiding the use of `QUndoCommands`. With styles, there is the collapsing of the style dict, the setting of formats and the checking of each text element in case any are images slow down the processes.

The other processes that scan the whole document again and again are fields (on every update), and index entries, and the edits that have to be made depending on how frequently the element occur.

Data retrieval and storage are likely as fast for the limitations, considering that text and steno data have to be linked, and custom data storage for paragraphs would mean cleanup of data that Qt does automatically. If loading from file, the original dict is kept in memory. Blocks that are modified are marked using `userState`. For saving, each paragraph's state is checked, and at the first block with `userState`, all subsequent paragraphs get data extracted and stored. 

Some funtions are called upon every cursor change: updating the steno display, updating the navigation display, and moving the tape to the proper spot. Responsiveness will speed up if all three are inactivated at the cost of less information visible.

## Editor memory

While it has not yet occurred, it is very likely that at some time, memory could pose a big problem with very big transcripts, or just multiple transcripts open. A memory saving strategy would be to use slots for element objects.

## `userState` in editor

The `userState` for each `QTextEdit` block holds one integer. Right now, it holds a 1 if the paragraph has been modified since opening, and -1 (Qt default.) It may be possible to assign more states by using binary, similar to the Qt enums.

## Transcript JSON format

An alternative to the regular JSON format would be using JSONL, with each line per paragraph. This would facilitate reading subsets of a file, and reducing memory when loading a transcript. 

Also, rather than keeping the backup document in memory, re-read the saved file until the first par with changed state, saving each line to new file, and then writing the new data before replacing old saved file with new one.

## Unit tests 

*In progress*

Tests should run from a dialog in editor using `unittest`. See this [link](https://stackoverflow.com/questions/20433333/can-python-unittest-return-the-single-tests-result-code) for returning a `TestResult`. Output should be redirected by specifying the `stream` argument for a `StringIO`.

Category of tests:


- Default config/style/dict
- Try writing
- Load transcript, new and old format
- Copy/paste between transcript
- Switch between transcripts (use recent file tab)