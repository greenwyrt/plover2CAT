# plover2CAT

Note: In line with the new Plover 5 release, Plover2CAT is releasing 4.0.0-alpha, which should retain all existing functionalities and is installable on Plover 5 by Github. All issues can be reported here or in Discord.

Plover2CAT is a plugin for Plover, the open-source stenography engine. If the only user requirement is to write steno on the computer, this plugin is not needed as Plover is more than sufficient. Plover2CAT supplements Plover by providing some features of a computer-aided-transcription (CAT) program.

## Features Overview

- a rich text editor with steno hidden underneath:
  - paragraph "block" type formatting
  - undo/redo history
  - conventional editing features such as cut/copy/paste and clipboard
  - find and replace for simple text, steno stroke, and untrans
  - spellcheck using the `spylls` library with user-selectable dictionaries
  - autosave transcripts
  - image insertion
  - navigation of heading paragraphs
  - typing input when Plover is disabled

- steno related features such as:
  - define/delete last untrans
  - define retroactive
  - insertion automatic paragraph affixes based on paragraph style
  - insertion of user defined fields
  - insertion of index entries
  - timestamped paper tape
  - creation and loading of transcript-specific dictionaries for each transcript

- audiovisual synchonization and recording

- captioning features such as:
  - separate window to display captions
  - customizable line lengths and word buffer between current text and text displayed
  - customizable minimum time interval between lines appearing
  - send captions to Microsoft Teams, Zoom, or OBS (both local and remote)

- export transcript formats (with style templates):
  - plain text
  - HTML
  - ASCII
  - SubRip
  - RTF/CRE 
  - OpenDocument Text 

- outline suggestions based on stroke history (powered by [Tapey Tape](https://github.com/rabbitgrowth/plover-tapey-tape) or [clippy_2](https://github.com/Josiah-tan/plover_clippy_2))

- transcript versioning using the `dulwich` library

- custom shortcuts for menu items

- translation of paper tape file into transcript

This plugin is built on Plover and inspired by [plover_cat](https://github.com/LukeSilva/plover_cat). 

New features are generally added over time when requested.


## Get Started

Documentation is linked online [here](https://plover2cat.readthedocs.io/en/latest/)

Start with #3 if you already have Plover installed and know how to install Plover2CAT from the command line.

1. [Install Plover](docs/tutorials/install-plover.md)
2. [Install Plover2CAT as a Plover plugin](docs/tutorials/install-plover2cat.md)
3. [Create new transcript in Plover2CAT](docs/tutorials/create-transcript.md)
4. [Write in the Plover2CAT editor](docs/tutorials/writing-editor.md)
5. [Export to text and Open Document Format](docs/tutorials/export-file.md)

Then review the available [how to ____](docs/README.md) articles.

## Getting help

Two ways: 1) Send a message over Discord. I am plants#4820 or 2) Open an issue on the [Github repository](https://github.com/greenwyrt/plover2CAT/issues).

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

See the docs for details of the implementation, and wished-for features. Much of Plover2CAT does not have unit tests.

# Contribute

Suggestions and bug reports are welcomed.

Contributions to the tutorials and how-to documentation are especially welcomed.

Contact me on the Plover discord as plants#4820 or open an issue on the repo. 




