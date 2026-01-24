# Dialogs

These dialogs will only appear after the menu item has been clicked. Some are modal, meaning they block the editor, and others are not.

## Paragraph Affix Dialog

Used to add and set paragraph affixes. Takes a dict of affixes defined for styles, and a list of all styles from the style file.

This dialog is modal.

See [how to add automatic paragraph affixes](../howto/auto_affixes.md).

## Field Dialog

Used to add and set fields. Takes a dict containing all field names and values for the document.

This dialog is modal.

See [how to define and insert a user field](../howto/userfield.md).

## Shortcut Editor Dialog

Used to set shortcuts for each menu item. Takes two lists, one of the text for each menu item, and the other the `objectName` of the menu item.

This dialog is modal.

See [how to set custom shortcuts for menu items](../howto/setcustomshortcuts.md)

## Index Editing Dialog

Used to create indexes, setting prefixes and visibility + add entries and descriptions for each index. Also adds 

This dialog is non-modal.

See [how to insert index entries](../howto/indices.md).

## Caption Dialog

Used to set parameters for caption display and host endpoint for remote captions. 

This dialog is modal.

See [how to set up and display captions](../howto/captions.md)

## Suggestion Dialog

Used to analyze transcript for common phrases and words that can then be added to the transcript dictionary. 

This dialog is non-modal.

See [how to generate suggestions from transcript](../howto/transcriptsuggest.md).

## Audio Recording Settings Dialog

Used to set parameters for audio recording on computer.

- Input Device:  Choices will be any audio inputs available to the computer such as a microphone. If the computer has a microphone, and the headphone also has mic input, these will be different choices in the menu.

- File Container: Choose the file container (type) desired. **Choose this before selecting an audio codec**.

- Audio Codec: The audio codec available will depend on the file container chosen. For some container types, such as `FLAC`, the only codec will be `FLAC`. Others, such as `MP4` will have multiple codecs available.

- Sample Rate and Channels can be left on default, and the software will pick the best fit.

- Encoding Mode

  - Constant Quality: The recording will be done based on the quality slider, varying the bitrate to keep the same quality.
  - Constant Bitrate: The recording will use the same bitrate throughout, but quality of the recording will vary.

By default, the audio recording is saved into the `audio` folder. 

See [how to set up and start audio recording](../howto/audiorecording.md), and relevant playback settings in [how to skip forward and back in an media file](../howto/audioseeking.md), [how to set up a time offset for syncing with writing](../howto/audiosync.md).
