# Exports

Plover2CATs can export transcripts in several plain and formatted documents for data exchange and viewing.

## Supported formatting in export

The table below summarizes what features are available for each export format.

| Format      | Richtext | Line \# | Timestamp | Page \# | Header/Footer | Char/Line | Lines/Page |
|-------------|----------|---------|-----------|---------|---------------|-----------|------------|
| Plain Text  | No       | No      | No        | No      | No            | No        | No         |
| Basic ASCII | No       | &check; | No        | &check; | No            | No        | No         |
| ASCII       | &check;\*| &check; | &check;   | &check; | &check;       | &check;   | &check;    |
| HTML        | &check;\*| &check; | &check;   | &check; | &check;       | &check;   | &check;    |
| ODT         | &check;  | &check; | &check;   | &check; | &check;       | &check;   | &check;    |
| *RTF/CRE*   |          |         |           |         |               |           |            |


\* No font support, indents and other layout is converted to closest approximation using spaces for padding.

Italics for features not yet supported but planned.

## Export file types

Each export file type is described below with caveats specific to each type.

Not all formatting can exported to all file types. For example, text files cannot have multiple fonts or different font sizes. Plover2CAT will do its best to emulate formatting for files that support only limited formatting. For example, line spacing settings will be rounded, so line spacing of 150% would become a line of text and an empty line (like double space). Tabstops, paragragh left and right margins, indents are all converted from inches to spaces (using 10 spaces per inch). Top and bottom padding for paragraphs are converted from inches to empty lines (using 6 lines per inch). As a result, the file contains a best-effort attempt to mimic formatting using text and spaces.

### Plain Text

The plain text format contains just pure text. Each paragraph becomes one line in the text document. This file will not contain any styling/formatting. 

### Basic ASCII

This is the ASCII format as specified in Ipos Eclipse. Page numbers begin on column 1, and are padded to 4 places. Each line of the text begins with line numbers starting on column 2, with text beginning on column 7 and is < 78 characters in length. Hard-coded into the code at this time is 25 lines per page. This export format will ignore style formatting.

### ASCII

This is an ASCII plain text format with support for line numbers and timestamps, using the style formatting.

### SubRip

Plover2CAT implements the simple SubRip (`*.srt`) captioning file format for exporting. This format requires all paragraphs to have an Audio Start Time property. The last paragraph for the audio needs an Audio End Time property, which can be set manually or by pressing `Stop` and having the time automatically be set for the paragraph. 

This file is not ready for use as subtitles, as it does not have the proper line widths. Captioning/subtitling software will be needed to actually do syncing of text to sound.

### OpenDocument Text

The Open Document Format (`ODF`) is an open source standard for documents based on XML. Plover2CAT will export `ODF` files which can be opened by most word processor software such as LibreOffice and Microsoft Word. `ODF` export is the most well-supported file type in terms of formatting, as Plover2CAT can [generate style templates](howto/generatestyletemplate.md) from `ODF` files and even use `ODF` files as [style templates](howto/generatestyletemplate.md) for formatting that is unsupported in Plover2CAT.

### RTF/CRE 

Plover2CAT offers exports to RTF/CRE, the commonly used data exchange format for transcripts. As a result, it is possible to import transcripts from Plover2CAT to commercial software such as CaseCatalyst. Plover2CAT exports a [subset](reference/rtf_support.md) of the [RTF spec](https://web.archive.org/web/20201017075356/http://www.legalxml.org/workgroups/substantive/transcripts/cre-spec.htm).