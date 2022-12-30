# How to enable autocompletion and add terms

Plover2CAT can offer suggestions in the form of popups when an user types the beginning of a string that matches from a list of candidate terms (and associated steno outlines), which is stored in a JSON file called `wordlist.json` in the `sources` folder.

To add candidate terms, select the text you wish to autocomplete and click on `Add Autocompletion Term` under `Steno Actions`. A dialog will appear showing the selected text, and an editable text box with the steno underlying the text. Make sure to edit the steno outline to the desired outline, if any.

To enable autocompletion, go to `Steno Actions` and click on `Autocompletion.` The editor will present choices for autocompletion based on the beginning of the string and the list of candidate choices. Users can use the up and down arrows to select a choice. By convention, the press of the `Enter` key will confirm the choice.

However, if the selection is performed through Plover, it is **highly recommended** that the user assigns a stroke to `{#Return}` to use to mimic the `Enter` key for autocompletion. If a stroke defined for `\n` is used, the unwanted side-effect of creating a new paragraph in the editor will occur.

Under the hood, the editor will insert the steno for the term into the editor when a candidate term is selected and inserted. If candidate terms were added without any steno outlines, those word would be "invisible" to search.

If autocompletion is enabled and there is no file called `wordlist.json` in the `sources` folder, nothing will happen, so make sure to add candidate terms before enabling autocompletion.

