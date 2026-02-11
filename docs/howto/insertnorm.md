# How to insert normal text 

Plover2CAT allows typing input from the keyboard when Plover is disabled. 

There are several ways to insert normal text that does not have associated steno data:
    - keyboard
    - Inserting Normal Text
    - Importing Text File
    - Normal Paste

## Keyboard

1. Make sure Plover is disabled.
2. Set the cursor in the editor and type using the keyboard.

The keys `Enter`/`Return` cannot be used to create a new paragraph. Use `Split Paragraph` if necessary.

`Backspace` will remove the character before the cursor, but only if the cursor is not at the start of the paragraph. In other words, `Backspace` cannot be used to combine paragraphs. Use `Merge Paragraphs` if necessary.

## Insert Normal Text

Click **Edit > Insert Normal Text** to insert normal text. Enter the text into the dialog window. This dialog accepts QWERTY keyboard input and also text from copying. This will work regardless of whether Plover is enabled or disabled. 

When `OK` is pressed, the text in the input is inserted into the editor at the cursor position. 

This function can also be triggered by the `Insert` key.

## Import Text File

Use **Insert > Text From File** to select a text file. All the contents of the file will be added starting at the present cursor position. Empty lines are not inserted.

## Normal Paste

Use **Edit > Normal Paste** to paste text from the system clipboard at the cursor location. Only text content will be inserted, and all formatting stripped. 

Similar to Import Text File, multiple lines/paragraphs can be inserted.