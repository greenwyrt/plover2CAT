# How to add custom dictionary

## Transcript dictionary

Select a JSON dictionary file from the filesystem and load into Plover2CAT with **Dictionary > Add Custom Dictionary**.

Use this instead of the Plover Add Dictionary function as Plover2CAT will copy the dictionary into the `dict/` folder of the transcript. The dictionary will be loaded when the transcript is opened and removed from Plover automatically when the transcript is closed.

The `default.json` that Plover2CAT creates for each transcript is a good place to add transcript-specific outlines if there is only a few.

## For all transcripts

To set a dictionary to be loaded for every transcript only in Plover2CAT, put the dictionary into a folder called `dict` within the `plover2cat` folder in the Plover configuration folder.