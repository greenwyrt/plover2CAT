# Commands

Editing is done through the `QUndoStack` mechanism for redo/undo-ing actions.

The two main functions are `steno_insert` and `steno_remove`, which insert and remove elements from the `userData` slot of the block in the `QTextEdit`.

## `steno_insert`:

Used to insert steno. 

- `document`: reference to `QTextDocument`
- `block`: integer, `blockNumber` in editor (do not take direct block reference in case it gets destroyed)
- `position_in_block`: integer, position of cursor within block
- `steno`: `element_collection` or one of many `text_element` types

## `steno_remove`

Used to remove steno. Cursor coordinate positions are set within command (even if already set outside) in case of redo/undo.

Attributes:
- `document`: reference to `QTextDocument`
- `block`: integer, `blockNumber` in editor
- `position_in_block`: integer, position of cursor within block (give earliest pos)
- `steno`: `element_collection` set after removal of steno
- `length`: length of text (aka number of backspaces)

## image_insert

Used to insert image into document

Attributes:
- `document`: reference to `QTextDocument`
- `block`: integer, `blockNumber` in editor
- `position_in_block`: integer, position of cursor within block (give earliest pos)
- `image_path`: path to image

## split_steno_par

- `document`: reference to `QTextDocument`
- `block`: integer, `blockNumber` in editor
- `position_in_block`: integer, position of cursor within block, location of split
- `space_placement`: value from Plover config

## merge_steno_par

- `document`: reference to `QTextDocument`
- `block`: integer, `blockNumber` in editor
- `position_in_block`: integer, position of cursor within block
- `space_placement`: value from Plover config
- `add_space`: whether to add space upon merge, default is `True`


## set_par_style:

- `block`: integer, `blockNumber` in editor
- `style`: name of style to be applied
- `document`:reference to `QTextDocument`
- `par_formats`: `dict` containing all block-level formats
- `txt_formats`: `dict` containing all char-level formats

Character formats have to be applied through the iterator of `QTextBlock` on individual `QTextFragment` elements to avoid applying a format on an image, over-riding its format, and causing it to revert to an object replacement charater.

## element_actions

This is a factory for generating QUndoCommands based on the element type.