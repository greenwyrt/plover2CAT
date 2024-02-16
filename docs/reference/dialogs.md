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

## Caption Dialog

Used to set parameters for caption display and host endpoint for remote captions. 

This dialog is modal.

## Audio Recording Settings Dialog

Used to set parameters for audio recording on computer.

- Input Device:  Choices will be any audio inputs available to the computer such as a microphone. If the computer has a microphone, and the headphone also has mic input, these will be different choices in the menu.

- Audio Codec: Windows systems like have PCM WAV at a minimum.

- File Container: A guess on the file format for the audio will be made based on the audio codec. If the codec is not one of the common ones, the audio file will not have a file extension, and users have to manually adding a file extension after recording is done.

- Sample Rate and Channels can be left on default, and the software will pick the best fit.

- Encoding Mode

  - Constant Quality: The recording will be done based on the quality slider, varying the bitrate to keep the same quality.
  - Constant Bitrate: The recording will use the same bitrate throughout, but quality of the recording will vary.

By default, the audio recording is saved into the `audio` folder. 
