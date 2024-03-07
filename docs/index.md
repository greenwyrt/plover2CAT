# Welcome to plover2CAT's documentation!

plover2CAT is a plugin for Plover, the open-source stenography engine. If the only user requirement is to write steno on the computer, this plugin is not needed as Plover is more than sufficient. plover2CAT supplements Plover by providing some features of a computer-aided-transcription (CAT) program.

```{toctree}
:maxdepth: 1
:caption: Getting Started
Install Plover <tutorials/install-plover.md>
Install Plover2CAT as a Plover plugin <tutorials/install-plover2cat.md>
Create new transcript in Plover2CAT <tutorials/create-transcript.md>
Write in the Plover2CAT editor <tutorials/writing-editor.md>
Export to text and Open Document Format <tutorials/export-file.md>
```

## Next Steps

The user should know what stenography is at this point, and can set up a machine / keyboard for writing through Plover before exploring and using the features of plover2CAT.

How to guides for plover2CAT's features (summarized below) can be accessed on the How To page. More in-depth overviews of the editor layout and menu items are located in References. 

```{toctree}
:maxdepth: 1
:caption: Contents
How To ___ <howto/index.md>
Reference <reference/index.md>
Development <discussion/development.md>
Code <api/index.md>
```


```{include} ../README.md
:start-after: program.
:end-before: New features
```

## Getting help

Two ways: 1) Send a message over Discord. I am plants#4820 or 2) Open an issue on the [Github repository](https://github.com/greenwyrt/plover2CAT/issues).

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
* [](search)


