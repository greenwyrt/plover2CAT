# Commands

Editing is done through the `QUndoStack` mechanism for redo/undo-ing actions. All changes to a transcript, including style changes, should be done through a `QUndoCommand`.

The `qcommands` module should contain all available `QUndoCommand` classes and classes/functions relating to generating any `QUndoCommand`.

The two main functions are `steno_insert` and `steno_remove`, which insert and remove elements from the `userData` slot of the block in the `QTextEdit`.


```{eval-rst}
.. automodule:: qcommands
    :members:
    :show-inheritance:
    :member-order: bysource
```



## Constructing a new ``QUndoCommand``

Each command has to subclass ``QUndoCommand``

Each subclass of `QUndoCommand` that acts on the transcript text must have the following parameters, *regardless of whether they are used in `redo` or `undo` functions*. This is to maintain consistency for action generation (future proof).

- `cursor`: reference to copy of present `QTextCursor`, such as `QTextEdit.textCursor()`, should be earliest position if cursor has selection 
- `document`: reference to `QTextEdit` transcript
- `block`: integer, `blockNumber` in editor (do not take direct block reference in case it gets destroyed)

Commands that act only on GUI style or data do not need to.

`block_state` is an attribute that is set within the `QUndoCommands` to indicate a block has been changed. For safety, even if an action is undone, the block's state is not reverted.

The `userState` attribute of each paragraph in the `QtextEdit` will be set to `1` (ie, is modified? True) if any `QUndoCommand` acted on it. Right now, this is to signify that the paragraph has been modified for use in saving the transcript, and it is not reset back to 0 even if the command is undone. This may change in the future.

The `QTextBlock` where edits are made within the `QUndoCommand` should be retried with `findBlockByNumber` and not directly with the current `QTextCursor`, in both `redo` and `undo`. This is especially important in `undo`. Then the cursor position should be set with `position_in_block` and `block` coordinates.
