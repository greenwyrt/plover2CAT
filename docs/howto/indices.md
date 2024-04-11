# Insert index entries

Plover2CAT supports indexed text, multiple indexes, with hidden or visible descriptions.

## Creating an index

Go to **Insert > Edit Indices**.  Click `Add New Index` to create a new index. The names of the indices are not editable from the editor, and are numbered starting from zero. 

## Index entry prefix

Fill in the prefix field with the text string to appear in front of each index entry, such as `Exhibit`. 

## Add index entry and set description

Index entries can only be created if there is an existing index. Fill in the `Index entry text` field, such as `1`, and press `Add new entry`. If the prefix was set as `Exhibit`, then the index entry inserted appears as `Exhibit 1`. Note a space is automatically added between the index entry prefix and the index entry text.

The text will appear in the first column of the table under `Entries for index`. Edit the cell in the same row under the `Description` column by double-clicking. A description is not necessary but can be added. An example would be `This is an exhibit.`

## Hiding descriptions

If the `Hide entry descriptions` box is checked, then the index entry descriptions do not appear in the text. 

Following the example, `Exhibit 1` will appear if the option is checked. But if descriptions are not hidden, `Exhibit 1This is an exhibit.` will appear. 

The lack of space between `1` and `This` is because the description text is directly added to the index text. In this way, users can add desired separators as required. For example, an user can set the description as `: This is an exhibit.` Then the full index entry in text will appear as ``Exhibit 1: This is an exhibit.`

## Saving changes and inserting

To save the changes such as new entries and descriptions, press either the `Save` or `Save & Insert` buttons. `Save` will save the data and update existing index entries in text if there are changes. `Save & Insert` will add the selected entry in the table to the text.

The `Close` button is used to close the dialog and discard any changes since the last `Save` or `Save & Insert` button was pressed.

## Multiple indices

Adding new index entries is the same process with multiple indexes. Users should pay attention to which index is selected from the dropdown list before adding new entries. What is important to note is changes are not saved if a user switches to a different index without saving. A second index may have a different prefix such as `Figure`

## Index entries have to exist

Entries are stored in the text, and collected for editing. This means that if an entry is created in the dialog, but not inserted into the text, it will be discarded upon dialog closure and not available the next time the `Edit indices` dialog is opened.

As the dialog is non-modal however, the user can keep the dialog open in the background and not lose entries that do not exist in the text until work is finished.

## Quick insert of index entries

An index entry can be quickly added through the **Insert > Index Entry** sub-menu. Each existing index will be a sub-menu item. 

If no text is selected, clicking the sub-menu item will bring up a dialog to enter the text. `OK` will insert the index entry.

If there is text selected in the editor, the selected text becomes the index name and an entry made from that text. Note that the steno information will be lost.

The "quick" occurs through Plover2CAT being able to specify shortcuts for each menu item. See [How to set custom shortcuts](setcustomshortcuts.md) for how to set shortcuts on menu items. With shortcuts, inserting an entry would be a process of 1) Activating sub-menu item by shortcut, 2) Input text, 3) press `OK` or input `Enter`.

## Generating the index

Plover2CAT does not generate an index from the entries. As indexes export properly to an ODT document or RTF/CRE file, indexes (with many custom options) can be created with LibreOffice and other software if needed.

