# Challenges of a steno-aware editor

The main challenge in creating a CAT editor is to keep track of the text and associated outlines that produced the text. Changes to the underlying steno data should be reflected in the visible, and also the other way around. If there was no need to keep the steno data and text connected, any normal word processor/text editor would work.

In Plover2CAT, text is displayed using a QTextEdit widget set to read-only, and the steno data for each paragraph is stored inside in the `userData` of the block. Whenever Plover2CAT is notified that Plover has received a stroke event, it checks whether the Plover engine has sent backspaces and text strings. Then Plover2CAT updates the steno data, storing the new stroke and corresponding text strings or trimming the previous string as necessary before updating the text display. The keypresses that Plover generates and uses to output are ignored by Plover2CAT. Using the two hooks and ignoring the Plover keypresses has the advantage of not losing data when paragraphs are deleted or created, as the steno data is modified before the text.

An alternative approach instead of storing steno data within QTextEdit would have been to maintain a separate data structure. But using `userData` kept the text and data closely associated, and removal of data when a paragraph was deleted is automatic through QTextEdit. In addition, retrieval of `userData` is fast through using the Qt QTextEdit API.

Adding and removing steno is implemented through `steno_insert` and `steno_remove` which subclass the QUndoCommand class which update `userData` and then the text of the QTextEdit, and can be undone/redone of the QUndoStack. Common editing functions such as `cut` and `paste` were then re-implemented using `steno_insert` and `steno_remove`. In addition, this made it easy to implement default behaviour for pressing the `Delete` key (removing character to right of cursor). However, by setting the QTextEdit to read-only to ignore keypresses that Plover generates, the editor also ignores actual keypresses, and consequently, a dialog input was needed to insert plain text.

## Merging and splitting paragraphs

With the QTextEdit, when a paragraph is deleted, so is the data associated with it. But when the basic Qt undo is used to restore the deleted paragraph, the data is still gone. This creates problems when a user merges paragraphs (by backspacing) or creates a new paragraph in the middle (pressing `enter`), common operations in a word processor. If two paragraphs are merged, the steno data stored in the second paragraph will disappear, and the first paragraph will have text from two different paragraphs, but the steno will only be of the first paragraph. Because of this limitation, there are two commands `split_steno_par` and `merge_steno_par` to be used when merging/splitting paragraphs. These functions will first copy the steno data, and manipulate it correctly. This way, the underlying steno will be merged and set properly rather than being lost.

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

## Steno across paragraphs

Sometimes, a stroke will have a translation that includes newlines `\n`. In cases like this, Plover2CAT will break up the string based on the `\n` into separate insertions. So `Line one\ntwo\nthree` will be three separate calls to `steno_insert`, with a call to `split_steno_par` between to generate a new paragraph. This is treated as one action for undo/redo even though there are actually five separate actions. It is not possible to undo in the middle.

The opposite of strings with newlines are `*` commands for Plover undo that crosses paragraph. This might be the result of the previous stroke containing new lines or in editing where the number of backspaces is greater than the number of characters in the paragraph. Plover2CAT calculates the position reached by the number of backspaces. Each time, `steno_remove` is used to remove as much text as possible until the cursor reaches the beginning of the paragraph, followed by a `merge_steno_par` call to merge the paragraphs, repeating until the number of backspaces is reached. This will also be treated as one action for undo/redo.