# How to set up and start audio recording

Plover2CAT can record audio through the computer's audio input if available. Video recording is not available.

To set up audio recording, go to the `Audio Recording` page in the `Toolbox` dock.

There are several dropdown menus which display the default choices based on the platform and operating system.

- Input Device:  Choices will be any audio inputs available to the computer such as a microphone. If the computer has a microphone, and the headphone also has mic input, these will be different choices in the menu.

- Audio Codec: Windows systems like have PCM WAV at a minimum.

- File Container: A guess on the file format for the audio will be made based on the audio codec. If the codec is not one of the common ones, the audio file will not have a file extension, and users have to manually adding a file extension after recording is done.

- Sample Rate and Channels can be left on default, and the software will pick the best fit.

- Encoding Mode

  - Constant Quality: The recording will be done based on the quality slider, varying the bitrate to keep the same quality.
  - Constant Bitrate: The recording will use the same bitrate throughout, but quality of the recording will vary.

By default, the audio recording is saved into the `audio` folder. 

Press `Record/Pause` under the `Audiovisual` menu to start recording. This is also available on the toolbar. Press again to pause. To stop recording, press `Stop Recording` in the `Audiovisual` menu.

Once audio recording has started, the settings cannot be changed. For example, if audio recording is paused, no settings can be changed. Pressing `Stop Recording` will end all recording, and then the settings can be changed.

Plover2CAT only allows one audio file per transcript. Trying to record again will result in the previous file being over-written. 
