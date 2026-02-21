# Welcome to plover2CAT's documentation!

plover2CAT is a plugin for Plover, the open-source stenography engine. If the only user requirement is to write steno on the computer, this plugin is not needed as Plover is more than sufficient. plover2CAT supplements Plover by providing some features of a computer-aided-transcription (CAT) program.

```{toctree}
:maxdepth: 1
:caption: Contents
Getting Started <tutorials/index.md>
How To ___ <howto/index.md>
Reference <reference/index.md>
Development <discussion/development.md>
Code <api/index.md>
```

New users are recommended to follow the [Getting Started](tutorials/index.md) tutorials first, which cover installation of Plover, Plover2CAT, writing into the editor, adding formatting, and exporting the transcript.

## Get Started

Start with #3 if you already have Plover installed and know how to install Plover2CAT from the command line.

1. [Install Plover](tutorials/install-plover.md)
2. [Install Plover2CAT as a Plover plugin](tutorials/install-plover2cat.md)
3. [Create new transcript in Plover2CAT](tutorials/create-transcript.md)
4. [Write in the Plover2CAT editor](tutorials/writing-editor.md)
5. [Export to text and Open Document Format](tutorials/export-file.md)


How to guides for plover2CAT's features (summarized below) can be accessed on the [How To](howto/index.md) page. More in-depth overviews of the editor layout and menu items are located in References. 


```{include} ../README.md
:start-after: program.
:end-before: New features
```

## Getting help

### Read the documentation

The [how to ___](howto/index.md) articles contain instructions on how to use different features of Plover2CAT.

The [reference](reference/index.md) articles contain useful information on how Plover2CAT data is organized and saved. 

### Contact information

1. Send a message over Discord. I am plants#4820
2. Open an issue on the [Github repository](https://github.com/greenwyrt/plover2CAT/issues)
3. Email greenwyrt@gmail.com

Helpful things to do: 
- Go to `Help` --> `About` to view the version number.
- Compress and attach the entire transcript directory, or the `*.tape` and `*.transcript` files. 
- If possible, add steps to reproduce the problem. 
- Add the log output from running Plover (debug) and attempt to cause the exact error.

## Development and Contribute

Suggestions and bug reports are welcomed on the [Github repository](https://github.com/greenwyrt/plover2CAT/issues).

Descriptions of the editor and data formats are in the references and design/development sections. The actual code and API are not fully documented at this moment but still in planning. Both code and text overviews are in flux and subject to change at any time.


## Acknowledgements

This plugin is under the MIT license.

Plover and PyQt are both under the GPL license. 

Fugue icons are by Yusuke Kamiyamane, under the Creative Commons Attribution 3.0 License.


Indices and tables
==================

* [](genindex)
* [](modindex)



