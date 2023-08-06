# Supported RTF/CRE features

Plover2CAT supports importing and exporting in RTF/CRE (Rich Text Format Court Reporting Extension) though only for a subset of features.

## RTF/CRE import

Import of RTF/CRE transcript files produced by other CAT software is not fully supported (due to different companies using their vendor specific flags).

`pyparsing` is used to import RTF/CRE files. Only a subset of the RTF/CRE spec is supported. Plover2CAT will extract the supported format flags and try to replicate settings such as page size and margin size. 

## RTF/CRE export

Plover2CAT will export a basic RTF/CRE as a data exchange file with other CAT software. The subset of flags for export and import is not the same, and consequently importing and then exporting an RTF/CRE file will not re-create the exact same file. See [exports](export.md) for supported RTF features.


## Supported flags

Flags with * are only outputted for export while ignored in imports.

Recognized RTF flags

    Default font (\deffont)*
    Creation time (\creatim \yr \mo \dy)
    Backup time (\buptim)*    
    Paper height (\paperh)
    Paper width (\paperw)
    Top margin (\margt)
    Bottom margin (\margb)
    Left margin (\margl)
    Right margin (\margr)
    New paragraph (\par)
    Stylesheet (\stylesheet)
    Style (\s)
    Next Style (\snext)
    Parent Style (\sbasedon)
    Style margins (\li \ri \fi \sb \sa)
    Text alignment (\ql \qr \qj \qc)
    Tabstops (\tx)
    Font table (\fonttbl)
    Font family (\froman \fswiss \fmodern \fscript \fdecor)
    Font (\f)
    Font size (\fs)
    Bold and italic (\b \i)
    Underline (\ul) (Only single solid line)

Recognized RTF/CRE flags

    Transcript (\cxtranscript)*    
    Revision number (\cxrev)*
    Frame rate per second (\cxframes)
    System (\cxsystem)*
    Number of lines per page (\cxnoflines)*
    Location of line number (\cxlinex)* - hardcoded
    Location of time code on line (\cxtimex)* - hardcoded
    Timecode (\cxt)
    Steno (\cxs)
    Automatic Text (\cxa)



