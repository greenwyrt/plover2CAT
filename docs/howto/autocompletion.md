# How to enable autocompletion and add candidates

Plover2CAT offers suggestions in the form of popups when an user types the beginning of a word or phrase. 

## Add candidates to autocompletion

Select the text you wish to add and click on **Add Autocompletion Term > Steno Actions**. Review the seleced text and editable steno in the dialog.

## Enable autocompletion

Go to **Steno Actions > Autocompletion**. The editor presents choices for autocompletion based on the beginning of the string and the list of candidate choices. Use the up and down arrows to select a choice. By convention, the press of the `Enter` key will confirm the choice.

It is **highly recommended** that the user assigns a stroke to `{#Return}` to use to mimic the `Enter` key for autocompletion if the selection is performed through Plover. If a stroke defined for `\n` is used, the unwanted side-effect of creating a new paragraph in the editor will occur.

## Details

Under the hood, the editor will insert the steno for the term into the editor when a candidate term is selected and inserted. If candidate terms were added without any steno outlines, those word would be "invisible" to search.

If autocompletion is enabled and there is no file called `wordlist.json` in the `sources` folder, nothing will happen, so make sure to add candidate terms before enabling autocompletion. Perform mass addition of candidates by editing `wordlist.json`.

