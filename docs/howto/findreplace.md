# How to find and replace text

There are three kinds of find: text, steno, and untranslated, each with different options available. Searches can be forward or backward, and wrap around if selected.

Use `Ctrl+F` to move to the find and replace pane.

## Text Find

1. Click on `Text` under `Search Types` to enable this. This will enable searching within translated text on the editor screen. 
2. Check/uncheck options for case sensitivity and whole word if available.
3. If any text in the editor is selected, it will automatically be put into the "Find" input box if `Ctrl+F` is used.
4. Enter text into the find box and then press `Next` to get the next occurrence or `Previous` to get the previous.

## Steno Find

Click on `Steno` under `Search Types` to enable this. 

This will search within the underlying steno. The search text must match the stroke completely ("Whole Word/Stroke" option checked by default) such that `ST` will match `ST` but not `ST-T`. The search text must be valid steno and there is no case-sensitivity.

Enter a steno stroke into the find box and then press `Next` to get the next occurrence or `Previous` to get the previous.

## Untrans Find

Click on `Untrans` under `Search Types` to enable this. 

This will search for any text that appears to be an untranslated steno stroke within the translated text. Only whole "words" in steno order and 3 or more letters long qualify as an untrans.

This search will find any untrans that match.

## Replace

If any of the three find methods has a match, it will be highlighted in the editor. The text in the "Replace" input box will replace the translated text. The underlying stroke data will not be changed.

## Replace All

This will search and replace all matches in the document with the replacement text.