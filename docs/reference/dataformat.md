# Data formats

This section describes the format of the main data-containing files. In most cases, these files do not need to be edited by hand.

## Config file

The configuration JSON file `config.CONFIG` contains transcript level settings. It is also the file selected in order to open a previously saved transcript. When a new transcript is created, the file is automatically generated. The file is placed in the root directory.

The key values in the JSON file are used to store transcript properties.

Possible key values are:

- `base_directory`: (Optional) this is a placeholder value for setting a root directory if transcripts are to be combined.
- `style`: relative path from config file to the selected style file (all files should be under `style` directory)
- `dictionaries`: list of relatively paths for transcript dictionaries (all files should be under `dictionary` directory)
- `page_width`: width of transcript page for export (in inches)
- `page_height`: height of transcript page for export (in inches)
- `page_left_margin`: left margin of transcript page for export (in inches)
- `page_right_margin`: right margin of transcript page for export (in inches)
- `page_top_margin`: top margin of transcript page for export (in inches)
- `page_bottom_margin`: bottom margin of transcript page for export (in inches)
- `page_max_char`: numeric value indicating maximum number of characters per line for export (0 means automatic)
- `page_max_line`: number value indicating maximum lines per character for export (0 means automatic)
- `page_line_numbering`: Boolean value indicating whether line numbering should be enabled in exports
- `page_linenumering_increment`: numeric value indicating every nth line is to be numbered (if supported in the export format)
- `page_timestamp`: Boolean value indicating whether text lines should be timestamped
- `header_left`: text for left header of each page
- `header_center`: text for center header of each page
- `header_right`: text for right header of each page
- `footer_left`: text for left footer of each page
- `footer_center`: text for center footer of each page
- `footer_right`: text for right footer of each page
- `user_field_dict`: dictionary containing default fields
- `enable_automatic_affix`: boolean, whether to enable automatic affixes
- `auto_paragraph_affixes`: dict containing affixes for styles, `{"style": {"prefix": "", "suffix": ""}}`
- `highlighter_colors`: dict holding style names: hex color codes, highlighting not applied if not defined, text will just be style text color, otherwise, highlighting overrides style color
For the header_* and footer_* keys, their text string values can contain a `%p` which will be replaced with the page number. 

This is the default `config.CONFIG` file that is created when a new transcript is created.

```
default_config = {
    "base_directory": "",
    "style": "styles/default.json",
    "dictionaries": [],
    "page_width": "8.5",
    "page_height": "11",
    "page_left_margin": "1.75",
    "page_top_margin": "0.7874",
    "page_right_margin": "0.3799",
    "page_bottom_margin": "0.7874",
    "page_line_numbering": False
}
```

Users should not have to edit the config file by hand as almost all values can be set through the GUI.

## Tape file

The tape file (named `{transcript_name}.tape`) is located in the root directory. It is saved at every stroke.

There are four fields separated by the `|` character:

- Time of stroke
- Audio time (if available)
- Position of cursor as (paragraph, position in paragraph, zero-based indexing)
- Steno keys pressed

This should make for easy parsing for other uses.

An example tape file would look like this if there is no audio time:
```
2001-01-01T01:23:45.678||(0,0)| T
2001-01-01T01:23:46.789||(0,4)|   K    A          T
```

## Transcript file

The transcript file (named `t{transcript_name}.transcript`) is located in the root directory.

The transcript file is in reality a JSON file. Each paragraph in the transcript is a key:value pair, with the paragraph number being the first level key, and a nested JSON object the value.

The nested JSON object holds the data on the paragraph itself. 

The keys for the nested JSON object are: 
- `creationtime`: timestamp for when the paragraph was created
- `edittime`: timestamp whn paragraph was last updated
- `audiostarttime`: timestamp of audio when paragraph was created (if available)
- `audioendtime`: timestamp of audio if audio was stopped when cursor was in paragraph (if available)
- `style`: string stating the style of the paragraph (should be one of the keys in the style file)
- `strokes`: array of serialized `text elements` (see [elements](../api/elements.md))
- `notes`: string for any notes the user has added to the paragraph

### Format < 2.0.0

Plover2CAT version < 2.0.0 use a different JSON structure. Any files with the old format will  be parsed and then converted when saving.

The nested JSON object holds the data on the paragraph itself. It has two keys, `text` and `data`. `text` holds the text for the paragraph as a text string. `data` is a nested JSON object.

`strokes` is an array of strokes. Each stroke in the `strokes` array is a three-element array, first element the timestamp for when the stroke occurred, second element the keys in the stroke, and third element the Plover output string.

It should be possible to recreate the `text` string by iterating through `strokes` and extracting the third elements.

## Style file

Users can select style files (both `ODF` and `JSON`) to format their exports. The `JSON` style files need to have specific keys to be valid. `ODF` style files will be correct and valid if they are created using word processors such as LibreOffice.

Each first-level key in the style file should be the name of the style, such as `Normal`, `Question`, `Answer`. The value of the key-value pairing is a nested JSON object describing paragraph and text properties.
Plover2CAT uses the Open Document Format names for paragraph and text properties and follows the same inheritance. As Plover2CAT uses the odfpy library for parsing and exporting, ODF attributes do not use the hypens present in the spec (ie `default-outline-level` is the attribute in ODF, but odfpy uses `defaultoutlinelevel`). These keys are optional.

Acceptable second-level key values are:
- `family`: string describing family of the style. At this time, all styles should use the `paragraph` value (as all styles are applied to text paragraphs).
- `defaultoutlinelevel`: a value between 1-10 or empty for ordinary text. At this time, all styles should use an empty value. 
- `parentstylename`: name of the family that this present style inherits from
- `nextstylename`: name of the style for the next paragraph
- `paragraphproperties`: nested JSON object describing paragraph formatting
- `textproperties`: nested JSON object describing text formatting

Any paragraph properties from the ODF spec are allowed as keys in the nested `paragraphproperties` object. Only the properties listed below can be edited through the Plover2CAT user interface.

- `textalign`: alignment of text (left/center/right/aligned)
- `textindent`: indent of first line in paragraph (in inches)
- `marginleft`: paragraph left margin (in inches)
- `marginright`: paragraph right margin (in inches)
- `margintop`: paragraph top margin (in inches)
- `marginbottom`: paragraph bottom margin (in inches)
- `linespacing`: string describing line spacing proportionally
- `tabstop`: one value describing one tabstop (in inches) or an array of tabstop values. Notice this is `tabstop` and not `tabstops` as specified by the ODF spec.

Due to style inheritance, there should be at least one base style in the file that other styles inherit from. It also means that styles should not have themselves set as their own parent style as that causes a loop.

Below is a commented template for one style for crafting styles by hand.

```

{
    "Name": { # name of the style
        "family": "paragraph",  # set to "paragraph"
        "defaultoutlinelevel": "", # heading level, 1-10, ordinary text has no level
        "parentstylename": "", # name of style the current style inherits properties from
        "nextstylename": "", # name of style for new paragraph after this one
        "paragraphproperties": {
            "textalign": "left/center/right/aligned", # has to be one of these four choices
            "textindent": "", # first line indent distance in inches ie "1in"
            "marginleft": "", # paragraph left margin in inches
            "marginright":"", # paragraph right margin in inches
            "margintop": "", # paragraph top margin in inches
            "marginbottom": "", # paragraph bottom margin in inches
            "linespacing": "" # line spacing using %, ie 200% for double space
            "tabstop": "" # can be one value ("2.0in") or a list for values ["1.0in", "1.5in", "2.0in"] for tabstops
        }
        "textproperties": {
            "fontname": "", # name of font
            "fontfamily": "", # font family
            "fontsize": "", # integer value for font size in pt, ie "12pt"
            "fontweight": "none/bold", # the style may not have "fontweight", but if it does, it has to be set as "bold"
            "fontstyle": "none/normal/italic", # the style may not have "fontsize" or set as "normal" or "italic"
            "textunderlinetype": "none/single", # the style may not have "textunderlinetyle" or it has to be set as "single"
            "textunderlinestyle": "none/solid" # the style may not have "textunderstyle" or it has to be set as "solid", but only if "textunderlinetype" is set
        }
    }
}


```
The `default.json` file looks like:

```
default_styles = {
    "Normal": {
        "family": "paragraph",
        "nextstylename": "Normal",
        "textproperties": {
            "fontfamily": "Courier New",
            "fontname": "'Courier New'",
            "fontsize": "12pt"
        },
        "paragraphproperties": {
            "linespacing": "200%"
        }
    },
    "Question": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Answer",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Answer": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Question",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Colloquy": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",  
        "paragraphproperties": {
            "textindent": "1.5in"
        }     
    },
    "Quote": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal", 
        "paragraphproperties": {
            "marginleft": "1in",
            "textindent": "0.5in"
        } 
    },
    "Parenthetical": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",
        "paragraphproperties": {
            "marginleft": "1.5in"
        }     
    }
}
```

These parameters attempt to recreate the NCRA's [transcript format guidelines](https://www.ncra.org/About/Transcript-Format-Guidelines).

If a property such as `linespacing` is not set (in the case of the `Question` style above), if the parent style has the setting (`Normal` has `linespacing` of `200%`), then the current style `inherits` that setting (`Question` style will also have `linespacing 200%`). If a style has a property set, and so does the parent style, the current style's property value overrides the parent style's value.


## Dictionary file

Dictionary files for the transcript are located under `dictionaries`. These should be formatted for Plover dictionaries, with outlines as keys.

An example is:

```
{
    "EPBG/HRAPBD": "England",
    "EPBG/HREURB": "English"
}
```

## Autocompletion file

A `wordlist.json` file in a `sources` directory within the transcript directory is needed containing prospective suggestions for autocompletion to fuction. This has to be a JSON with the format `suggestion` : `steno`. Spaces are allowed in `suggestion`, but all whitespace (tabs and new lines) will be replaced by spaces.

An example is:
```
{
	"doctor": "TKR",
	"England": "EPBG/HRAPBD",
	"English": "EPBG/HREURB",
	"Europe": "AO*URP",
	"French": "TPREFRPB",
	"God": "TKPO*D"

}

```

Notice that this reverses the key:value of a Plover dictionary.
