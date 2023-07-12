Plover2CAT is a plugin for Plover, the open-source stenography engine. If the only user requirement is to write steno on the computer, this plugin is not needed as Plover is more than sufficient. Plover2CAT provides some of the features a computer-aided-transcription (CAT) program has to produce a transcript for captioning or other purposes. 

# Features Overview:

- [x] a rich text editor with steno hidden underneath
- [x] paragraph "block" type formatting
- [x] conventional editing features such as cut/copy/paste while keeping steno data attached
- [x] undo/redo history
- [x] automatic creation and loading of transcript-specific dictionaries for each transcript
- [x] find and replace for simple text, steno stroke, and untrans
- [x] retroactive define, and define last translate with replacement of all previous occurrences and new outline sent to transcript dictionary
- [x] an audiovisual player, with controls for timing offset, playback rate, skipping forward and back
- [x] synchronization of steno with the audio/video file for transcription
- [x] audio recording synchronized with steno (file format dependent on codecs in operating system)
- [x] export transcript to plain text, HTML, ASCII, SubRip, RTF/CRE and Open Text Document formats (with style templates)
- [x] saves paper tape with keys pressed, position of cursor in document, and timestamps at each stroke
- [x] suggestions based on stroke history (powered by Tapey Tape), updated every paragraph
- [x] spellcheck using the `spylls` library, ability to select spellcheck dictionaries 
- [x] versioning using the `dulwich` library, switch between previously saved transcript states
- [x] custom shortcuts for menu items
- [x] translation of paper tape file into transcript
- [x] basic import of RTF/CRE transcript
- [x] import of images and export into supported formats
- [ ] 
This plugin is built on Plover and inspired by [plover_cat](https://github.com/LukeSilva/plover_cat). 


## Get Started

Start with #3 if you already have Plover installed and know how to install Plover2CAT from the command line.

1. [Install Plover](docs/tutorials/install-plover.md)
2. [Install Plover2CAT as a Plover plugin](docs/tutorials/install-plover2cat.md)
3. [Create new transcript in Plover2CAT](docs/tutorials/create-transcript.md)
4. [Write in the Plover2CAT editor](docs/tutorials/writing-editor.md)
5. [Export to text and Open Document Format](docs/tutorials/export-file.md)

Then review the available [how to ____](docs/README.md) articles.

## Getting help

Two ways: 1) Send a message over Discord. I am plants#4820 or 2) Open an issue on Github.

Helpful things to do: 
- Go to `Help` --> `About` to view the version number.
- Compress and attach the entire transcript directory, or the `*.tape` and `*.transcript` files. 
- If possible, add steps to reproduce the problem. 
- Add the log output from running Plover (debug) and attempt to cause the exact error.


# Acknowledgements

This plugin is under the MIT license.

Plover and PyQt are both under the GPL license. 

Fugue icons are by Yusuke Kamiyamane, under the Creative Commons Attribution 3.0 License.

# Development

Plover2CAT at present, is one gigantic class, and with absolutely no tests. See the user manual for details of formats such as stroke data, and wished-for features.

# Contribute

Suggestions and bug reports are welcomed.

Contributions to the tutorials and how-to documentation are especially welcomed.

Contact me on discord or open an issue on the repo. 




