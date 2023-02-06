# How to import a RTF/CRE transcript file

RTF/CRE transcript files are created by CAT software, containing steno strokes, timecodes, and text among other data.

Plover2CAT can import an RTF/CRE file through `File` --> `Import RTF/CRE`. Plover2CAT will also try to import the page and style formatting encoded in the RTF/CRE file. It is best to open a new transcript and then import a RTF/CRE file, as the existing transcript will be over-written. 

Not all content in the RTF/CRE file will be imported. While Plover2CAT tries to support the main features of the RTF/CRE spec, CAT software vendors also use their own undocumented RTF flags for content and formatting. Those vendor flags are not able to be imported at this point. However, future development may include vendor specific RTF/CRE flags if users are able to provide examples of such files and able to pinpoint what those flags do. See [Supported RTF/CRE Features](../reference/rtf_support.md) for supported RTF flags.

