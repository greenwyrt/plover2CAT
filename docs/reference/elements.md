# Custom Text Elements

The out-of-the-box features in QTextEdit and QUndoStack are very good for basic rich-text, images, lists, and tables. The initial approach of keeping a list with userData with each paragraph text works very well when the transcript only contains text. However, custom functionality is needed when going beyond just pure text, such as images, "indexing", and "automatic text", so different text elements are implemented as custom classes, and can be held in a custom list class.

For example, an image element can contain more data than just pure text, such as the image location, dimensions. If this is a figure reference, then there has to also be an identifier, optionally figure number and caption. One way would be to switch from lists to dictionaries directly but classes offer more benefits.

These text elements are treated different in certain formats, ie images in ODF vs plain text. For a complete transcript, the image in the ODF should be embedded (since that functionality is available for ODF files) and use odfpy node elements. However, if the export is plain text, there shouldn't be an image included as it is not possible. The representation of the text element will differ depending on file format.

Certain elements also have different lengths compared to what should be visualized, like a functional and a text display length. For example, while exhibit text can be something like `Exhibit 2`, which is 9 chars worth of horizontal space, it should be treated as one entity, for example, a backspace should remove the entire string, not just the tab character, and has a functional length of one.

There is also "automatic text", which is considered a part of the preceding or succeeding "translation", and has a functional length of 0.

## Element Classes

### text_element

This is the base class all element classes inherit from. The class subclasses `UserString`

It has the attributes:

- `element`: "text"
- `data`: string that can be set
- `time`: timestamp, either set or automatically taken from time of creation

It has the methods:

- `__len__`: returns length of string
- `__getitem__`: returns new instance after deepcopy
- `__repr__`: representation as `dict`
- `__add__`: adds together text, and updates time from other
- `length`: returns length of string, here as placeholder in order to keep consistency with other subclassed elements, the functional length
- `split`: splits text string on whitespace (re from textwrapper), returns list of elements containing each text piece separately, but same otherwise as original
- `from_dict`: can populate class using a dict
- `to_display`: formatted string for display in GUI, should be a string for three lines, 1) icon letter, 2) element data, if any, 3) text
- `to_json`: returns dict of attributes
- `to_text`: returns "text" representation as imagined for QTextEdit
- `to_rtf`: returns `RTF/CRE` string
- `to_odt`: receives an ODF paragraph element and the document, adds text to it
- `replace_initial_tab`: replaces first tab in string

### stroke_text

Based on `text_element`, used to represent one or more strokes with corresponding text

It has the additional attributes:

- `element`: "stroke"
- `stroke`: stroke(s)
- `audiotime`: audio timestamp

Overriding methods:

- `__add__`: will only combine elements but not across word boundaries (spaces)
- `to_rtf`
- `to_display`

`stroke_text` still has the `text` attribute and so the `to_text` of a series of `stroke_text` objects will re-create the translations.

### image_text

It has the additional attributes:

- `element`: "image"
- `path`: path to resource/asset
- `width`: width of image
- `height`: height of image

Overriding methods:

- `__add__`: throws error
- `length`: 1
- `to_display`
- `to_odt`    

Upon creation, the ￼OBJECT REPLACEMENT CHARACTER is added as `data`.



### text_field

It has the additional elements:

- `name`: name of field
- `user_field_dict`: dict containing all assigned fields

Overriding methods:

- `__add__`: throws error
- `length`: 1
- `to_json`: do not output `user_field_dict`, no need for a copy of all fields with each element
- `to_display`:
- `to_text`
- `to_rtf`
- `to_odt`

New method:

- `update`: checks the `user_field_dict` and assigns value to `data`, "updating" if the value in the dict for the `name` has been changed

The `user_field_dict` by default uses the global `user_field_dict` object. Need to specify if a different dict is to be used.

### automatic_text

Based on `stroke_text`, used to represent "automatic" text, or text added not by the user.

It has the additional attributes:

- `element`: "automatic"
- `prefix`: text to place before string
- `suffix`: text to add after string

It has the methods:

- `__add__`: throws error
- *`length`*: the length of the text only, the element's "functional" length
- `__len__`: returns length of prefix + text + suffix
- `to_text`: string of prefix + text + suffix
- `to_rtf`: adds `cxa` commands to either side of basic `cxt + cxs` command if affixes exist
- `to_display`


### conflict_text

TODO

really needed with RTF imports, not so much with Plover


### index_text

It has the additional attributes:
    - `element`: "index"
    - `prefix`: string to place before "number"
    - `indexname`: index that element belongs to
    - `description`: description of the index entry 
    - `hidden`: whether description is hidden or not

Overriding methods:

- `__add__`: throws error

The actual "number" for the exhibit is stored in the `text` attribute. 

Has non-breaking space in `to_text` so that "prefix" and "number" are always together even for text formats.

## element_collection

This is the container holding a list of elements. It subclasses `UserList` and overrides some methods. Despite being an `UserList` list, the methods mean it behaves like a `string` in many ways.

- `__str__`: returns the `to_text` of all the elements in one string
- `lengths`: returns list of functional lengths for each element
- `lens`: returns list of "text" lengths for each element
- `__len__`: returns sum of `lens`
- `__getitem__`: see below.
- `element_count`: integer, number of elements in collection, the true `len` in the conventional sense for a list
- `to_json`: returns list of serialized `dict` objects
- `to_text`: text string combining all elements
- `to_rtf`: returns string containing RTF representations of elements
- `to_odt`: calls `to_odt` on each element to add to the paragraph element, also document if needed
- `to_display`: returns list of display strings for elements
- `remove`: removes based on specified functional position start/stop, returns removed elements
- `insert`: insert into position based on the functional position
- `stroke_pos_at_pos`: returns tuple of text start, stop for element at text `pos`
- `element_pos`: returns tuple of text start, stop for element at `index` in collection
- `remove_steno`: removes elements from `start` to `end` (text) position
- `extract_steno`: retrieves elements from `start` to `end` (text) position, does not modify original collection
- `insert_steno`: inserts `element_collection` at (text) `pos`, will split up elements in collection if needed
- `starts_with`: check if text starts with `char`
- `ends_with`: check if text ends with `char`
- `remove_end`: removes `char` end of text string, will remove entire element if `char` is only text in element
- `remove_begin`: check if text starts with `char`, remove `char` from first element if text starts with `char`
- `add_begin`: add `char` to beginning of first element
- `add_end`: add `char` to end of last element
- `stroke_count`: only added because RTF needs it for now, counts the number of strokes in collection
- `search_strokes`: returns text positions for matches to underlying strokes, None if no match
- `search_text`: text search through `re.finditer`
- `collection_time`: returns earliest timestamp in collection, or latest if `reverse = True`
- `replace_initial_tab`: replaces initial tab in place within collection, hardcoded to be only within first 4 chars
- `merge_elements`: collapses collection elements using `_add__` method of elements in try-except

### Usage

Slices of the class ie `collection[0:4]` is used to obtain `element_collection` of all elements within the collection in the range `start, stop` based on the functional lengths of each element. Use `extract_steno` to use `text` coordinates.

Indexing of class ie `collection[1]` is used to access each element of the collection (returns a `element_collection` class containing only one element). Use `.data` to access the element itself.

`element_collection` methods are heavily biased for `stroke_text` elements relative to other elements.

## `element_factory`

Factory function to generate `elements` from `dict` objects. Use to recreate elements from `JSON` files.

```
element_list = stroke_collection.to_json() 
el_factory = element_factory()
[el_factory.gen_element(element_dict = i) for i in element_list]
```

## `translate_coords`

A helper function, given two lists of 1) text  2) functional cumulative lengths and the text position `pos`, returns the functional position. This is a shortcut compared to looping over each element to get coordinates.

## `backtrack_coord`

A helper function, given position in text, number of backspaces, list of text and functional lengths, return ending text position. Like `translate_coords`, `bisect` is used to avoid looping over each element, important as `element_collection` grows bigger. If more `backspaces` than exists, function returns a negative, the number of backspaces beyond.

## `steno_wrapper`

A helper function subclassing `TextWrapper` for wrapping an `element_collection`. This returns a list of lists of elements, not collections.

## Reminders for any new element

1.  Determine element functional length
2.  Add any new attributes, check if ODF spec has corresponding equivalent, and use same names if possible
3.  Create 1) text representation and 2) letter to use in steno display
4.  Check if RTF spec or RTF/CRE spec has corresponding equivalent, create formatted string by overriding, otherwise, just simple text
5.  Create ODF element by overriding, otherwise just simple text
6.  Determine if element needs updating methods or not.
7.  Add to `element_factory` so able to generate element
8.  Create `QUndoCommand` if necessary, and add to `element_action` generator
9.  Create GUI/shortcuts/functions for insertion