# Development

plover2CAT's development is built on top of the Qt Framework and the Plover engine hooks. The various pages discuss certain challenges and reasons for why plover2CAT has developed in certain directions.

```{toctree}
:maxdepth: 1
Challenges of a steno-aware editor <stenoeditor.md>
Lossy steno data <lossysteno.md>
Plover engine hooks <enginehooks.md>
Transcript data formats <transcriptdata.md>
```

The sections below list things that could be part of future versions.

## Minor possible improvements

- rename audiovisual to media in UI
- add warning about fields in text if removed from dict
- apply same style to multiple paragraphs (cursor highlighting multiple paragraphs)

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

Paragraphs with certain styles could get a highlight color.


## Richtext Features for indexes and tables

While richtext editing has been enabled, some common features of word processors and professional CAT software are missing. Primary ones are 1) embedding images (implemented), 2) table of contents/index and 3) tables.

Tables are likely more difficult to implement and may require an editor widget.

## Refactoring editor

The editor should be refactor into a smaller class.

Methods that exclusively work on the `QTextEdit` could possibly be extracted and refactored from the `PloverCATWindow` into the `PloverCATEditor` custom class.

## Editor speed

At present, when loading a transcript, the main bottleneck in speed comes from rendering paragraph styles for display and setting page format on the document. Populating the editor with text is incredibly fast by avoiding the use of `QUndoCommands`. With styles, there is the collapsing of the style dict, the setting of formats and the checking of each text element in case any are images slow down the processes.

The other processes that scan the whole document again and again are fields (on every update), and index entries, and the edits that have to be made depending on how frequently the element occur.

Data retrieval and storage are likely as fast for the limitations, considering that text and steno data have to be linked, and custom data storage for paragraphs would mean cleanup of data that Qt does automatically. If loading from file, the original dict is kept in memory. Blocks that are modified are marked using `userState`. For saving, each paragraph's state is checked, and at the first block with `userState`, all subsequent paragraphs get data extracted and stored. 

Some funtions are called upon every cursor change: updating the steno display, updating the navigation display, and moving the tape to the proper spot. Responsiveness will speed up if all three are inactivated at the cost of less information visible.
