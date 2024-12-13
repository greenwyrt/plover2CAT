# Transcript Folder Structure

The transcript folder contains all necessary data and is designed to be portable, so that Plover2CAT can open it anywhere it is moved.

The transcript folder is created through `Create New` on the menu. By default, the folder is named `transcript-{timestamp}` with `timestamp` in the format of `YYYY-MM-DDTHHMMSS`. Several default folders and files are created within this transcript folder.
This folder will be initially created in the temporary directory of the user's operating system.
On the first save, the user will be prompted to select a location on the filesystem for the transcript to be saved to. 
At this time, the use can also input a name for the transcript.

## Folder Structure 
The basic structure has five folders and three files.

`{transcript_name}` will be the name the user inputs or `transcript-{timestamp}` by default.

```
{transcript_name}/
    assets/
    audio/
    dict/
        transcript.json
        custom.json
        dictionaries_backup
    exports/
    sources/
        wordlist.json
    spellcheck/
    styles/
        default.json
        styles.odf
    {transcript_name}.transcript
    {transcript_name}.tape
    config.CONFIG
```

## Folder Description

- assets: contains images to load into document

- audio: contains audio/video files, such as those recorded in Plover2CAT

- dict: contains transcript-specific JSON files in Plover dictionary format that will be loaded when the transcript is opened

- exports: contains the transcript in export formats such as RTF/CRE and HTML

- sources: contains a `wordlist.json` that contains autocomplete suggestions

- spellcheck: contains any Hunspell `*.dic` and `*.aff` files used for spellchecking

- styles: style files (JSON or ODF) that will format export files that use formatting

## File Description

`config.CONFIG` is the configuration file containing settings for the transcript. This is the file Plover2CAT will need to recognize the directory as a transcript to open.

The `{transcript_name}.tape` file holds all strokes written in the editor, and even strokes written when the editor is not in focus if `Capture All Output` is activated. This file is updated at each stroke, and even when the transcript is not saved when exiting Plover2CAT, it does not affect the contents in the tape file.

The `{transcript_name}.transcript` file is a JSON holding stroke and styling information for the transcript. 

For details on how these files are structured, refer to [data formats](dataformat.md)


