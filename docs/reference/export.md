# Exports

Plover2CATs can export transcripts in several plain and formatted documents for data exchange and viewing.

## Supported formatting in export

The table below summarizes what features are available for each export format. For formats where features are not available, the closest text representation is used to replace it.

Format        | Plain Text | Basic ASCII | ASCII     | HTML      | ODT     | RTF/CRE
---           | ---        | ---         | ---       | ---       | ---     | ---
Richtext      | No         | No          | &check;\* | &check;\* | &check; | &check;
Line \#       | No         | &check;     | &check;   | &check;   | &check; | *No*
Timestamp     | No         | No          | &check;   | &check;   | &check; | No
Page \#       | No         | &check;     | &check;   | &check;   | &check; | No
Header/Footer | No         | No          | &check;   | &check;   | &check; | *No*
Char/Line     | No         | No          | &check;   | &check;   | &check; | No
Lines/Page    | No         | No          | &check;   | &check;   | &check; | *No*
Images        | No         | No          | No        | No        | &check; | &check;
Fields        | No         | No          | No        | No        | &check; | &check;
Headings      | No         | No          | No        | No        | &check; | No
Index entries | No         | No          | No        | No        | &check; | &check;

\* No font support but indents and other layout are converted to closest approximation using spaces for padding.

Italics for features not yet supported but planned.

## Export file types

Each export file type is described below with caveats specific to each type.

Not all formatting can exported to all file types. For example, text files cannot have multiple fonts or different font sizes. Plover2CAT will do its best to emulate formatting for files that support only limited formatting. For example, line spacing settings will be rounded, so line spacing of 150% would become a line of text and an empty line (like double space). Tabstops, paragragh left and right margins, indents are all converted from inches to spaces (using 10 spaces per inch). Top and bottom padding for paragraphs are converted from inches to empty lines (using 6 lines per inch). As a result, the file contains a best-effort attempt to mimic formatting using text and spaces.

### Plain Text

The plain text format contains just pure text. Each paragraph becomes one line in the text document. This file will not contain any styling/formatting. 

The `export_text` method directly write the editor text to file.

### Basic ASCII

This is the ASCII format as specified in Ipos Eclipse. Page numbers begin on column 1, and are padded to 4 places. Each line of the text begins with line numbers starting on column 2, with text beginning on column 7 and is < 78 characters in length. Hard-coded into the code at this time is 25 lines per page. This export format will ignore style formatting.

The `export_plain_ascii` method wraps editor text and adds line numbers and page numbers according to file format.

### ASCII

This is an ASCII plain text format with support for line numbers and timestamps, using the style formatting.

### SubRip

Plover2CAT implements the simple SubRip (`*.srt`) captioning file format for exporting. This format requires all paragraphs to have an Audio Start Time property. The last paragraph for the audio needs an Audio End Time property, which can be set manually or by pressing `Stop` and having the time automatically be set for the paragraph. 

`export_srt` uses block-level `audiostarttime` and `audioendtime` to create `srt` file. This file is not ready for use as subtitles, as it does not have the proper line widths. Captioning/subtitling software will be needed to actually do syncing of text to sound.

### OpenDocument Text

The Open Document Format (`ODF`) is an open source standard for documents based on XML. Plover2CAT will export `ODF` files which can be opened by most word processor software such as LibreOffice and Microsoft Word. `ODF` export is the most well-supported file type in terms of formatting, as Plover2CAT can [generate style templates](howto/generatestyletemplate.md) from `ODF` files and even use `ODF` files as [style templates](../howto/generatestyletemplate.md) for formatting that is unsupported in Plover2CAT.

### RTF/CRE 

Plover2CAT offers exports to RTF/CRE, the commonly used data exchange format for transcripts. As a result, it is possible to import transcripts from Plover2CAT to commercial software such as CaseCatalyst. Plover2CAT exports a [subset](rtf_support.md) of the [RTF spec](https://web.archive.org/web/20201017075356/http://www.legalxml.org/workgroups/substantive/transcripts/cre-spec.htm).

## Export from editor

The editor offloads exporting to another thread through `documentWorker`.

`documentWorker` takes:

- `document`: copy of transcript in dict form (save transcript automatically to update)
- `path`: export file path
- `config`: transcript config
- `styles`: dict of styles for transcript
- `user_field_dict`: dict of fields
- `home_dir`: transcript dir path

`documentWorker` has two signals:

- `progress`: sent after generating a paragraph with paragraph number, updates progress bar in editor
- `finished`: sent after export file is created

Each export format has its own method called from editor.

### Wrappers and helpers

Wrapping of paragraphs is done with `steno_wrap_*` after appropriate formatting with `format_*_text`, resulting in a `dict` containing `{line_num: line_data_dict}`. 