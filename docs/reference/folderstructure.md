# Transcript Folder Structure

The transcript folder is created through `Create New` on the menu. By default, the folder is named `transcript-{timestamp}` with `timestamp` in the format of `YYYY-MM-DDTHHMMSS`. Several default folders and files are created within this transcript folder.

## Folder Structure 
The basic structure has five folders and three files.

```
transcript-{timestamp}/
    audio/
    dictionaries/
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
    transcript-{timestamp}.transcript
    transcript-{timestamp}.tape
    config.CONFIG
```

## Folder Description

- audio: contains audio/video files, such as those recorded in Plover2CAT

- dictionaries: contains transcript-specific JSON files in Plover dictionary format that will be loaded when the transcript is opened

- exports: contains the transcript in export formats such as RTF/CRE and HTML

- sources: contains a `wordlist.json` that contains autocomplete suggestions

- spellcheck: contains any Hunspell `*.dic` and `*.aff` files used for spellchecking

- styles: style files (JSON or ODF) that will format export files that use formatting

## File Description

`config.CONFIG` is the configuration file containing settings for the transcript. This is the file Plover2CAT will need to recognize the directory as a transcript to open.

The `transcript-{timestamp}.tape` file holds all strokes written in the editor, and even strokes written when the editor is not in focus if `Capture All Output` is activated. This file is updated at each stroke, and even when the transcript is not saved when exiting Plover2CAT, it does not affect the contents in the tape file.

The `transcript-{timestamp}.transcript` file is a JSON holding stroke and styling information for the transcript. 

For details on how these files are structured, refer to [data formats](dataformat.md)


