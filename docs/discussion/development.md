# Development

Plover2CAT at present, is one gigantic class, and with absolutely no tests.

The sections below list things that could be part of future versions.

## Parsable action logging

The log messages are not formatted consistently or easy to decipher.

## RTF/CRE

RTF import/export has been implemented selectively. 

More RTF example files from different companies are needed to test import capabilities as different CAT software have their own own flags.

## Autocomplete enhancement

Right now, autocomplete suggestions come from a pre-set list. The engine should update in near-realtime and take suggestions from the present text, or other transcript json/rtf. However, there could be performance considerations if this is a large transcript. Engine input processing may need to be offloaded to a separate thread on regular intervals or initialized by the user (ie, when user knows that there is time to update) or both.

Occurrences of words can be counted with a `Counter`, and the first occurrence can be searched for steno in the blocks.

Autocomplete and next word prediction are not the same things.

## Enhancing search types

Possible new search types: 
- time of stroke, or time of paragraph
- exact, starts with, ends with, contains, partial stroke
- filters for # of strokes, includes numbers/punctuation etc 


## Alternative formats

HTML: The present HTML format is just the ASCII text in a code block wrappd up with html tags. HTML can be much more flexible (ie table of contents, search, images, embedded audio etc), even if the plain text structure has to be kept.

Latex: suggested

Epub: More of a reading format

Steno-Annotated ODF: Plover2CAT should produce an annotated document, putting raw steno in the `ruby` element to annotate the corresponding words. This takes advantage of the annotations which are originally for Asian language pronunciation.

## Preview of search and replace

Search and replace is done "blindly" in the case of replace all, and also more timeconsuming if done one by one. A preview might allow for a quick check, summarizing the number and showing the context.

## Style highlighting

Paragraphs with certain styles could get a highlight color.


## Custom classes for text objects

*This idea is only partially implemented*

The `userData` for each text block is just a list of three-element lists. This works well for just simple time-stroke-string. Professional CAT programs can do things such as display conflicts and index entries. However, those have either variable lengths or are one in length and have to be treated differently than normal steno. With custom classes, non-stroke entities can emit custom len values, and be handled differently in export. 

This likely requires changing the `.transcript` file format in some way, likely a major revision. This should be done before adding images/tables.

Class steno_object
    text
    stroke(s)
    timestamp
    audiotimestamp
    str <- text
    dict
    len <- text length
    length <- tag length

Class reference_object
    text is one char " "
    stroke is empty
    timestamp is empty
    audiotimestamp is empty
    str is one char
    len is one char
    ref_anchor is an id
    len is 1
    length is length of id and more

Why? Image exhibit reference as "Exhibit 1. caption blah" within text. This should be treated as one character, and have unique id for referencing.

## Richtext Features for indexes and tables

While richtext editing has been enabled, some common features of word processors and professional CAT software are missing. Primary ones are 1) embedding images (implemented), 2) table of contents/index and 3) tables.

Indexes (in reality, a table of contents) for ODF depends on having "heading" styles. This can be integrated. RTF table of contents is possible (based on the spec). The difficulty will be keeping track of the text in the editor selected for table of contents if there is custom text. 

Tables are likely more difficult to implement and may require an editor widget