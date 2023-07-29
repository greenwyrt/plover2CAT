# Dialogs

Plover2CAT dialogs have their own UI and code files as they subclass `QDialog`. In general, these dialogs will receive a dict along with other parameters, and changes are made to the internal dict. After `accepted`, the dialog dict is then accessed from outside.

## Paragraph Affix Dialog

Used to add and set paragraph affixes. Takes a dict of affixes defined for styles, and a list of all styles from the style file.

This dialog is modal.

## Field Dialog

Used to add and set fields. Takes a dict containing all field names and values for the document.

This dialog is modal.

## Shortcut Editor Dialog

Used to set shortcuts for each menu item. Takes two lists, one of the text for each menu item, and the other the `objectName` of the menu item.

This dialog is modal.

## Index Editing Dialog

Used to create indexes, setting prefixes and visibility + add entries and descriptions for each index. Also adds 

This dialog is non-modal.
