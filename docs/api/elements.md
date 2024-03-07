# Custom Elements

`text_element` is the base class other element classes inherit from. It represents a text string that can be converted to various formats. 

Each time steno is written, a `stroke_text` object is created containing the stroke and output text from Plover which is then inserted into the editor. `stroke_text` objects should make up most of the data in the editor, rather than `text_element`, used mainly for keyboard input due to edits.

The text in each paragraph of the editor is composed of various elements represent written (steno) text, typed text, or other special kinds of text, all of which subclass the base `text_element` class.

Each element has text can either be treated as a string of text that can be manipulated (sliced, modified, partially deleted) or as one unit.

Elements are stored together in an `element_collection` that is then stored in the `userData()` of a `QTextBlock` when shown in the GUI editor.

Each `text_element` (and classes that inherit from it) as well as `element_collection` can be converted to different representations, such as text, JSON, and RTF, with the `to_text()` returning the string representation to display in a `QTextEdit`.

## Combining elements

Only strictly text and stroke elements can be combined through `__add__` and `__radd__`, so while `automatic_text` subclasses `stroke_text`, the two should not be combined. This is primarily for the use of collapsing elements into word chunks, as `pre` and `pare ` may be two stroke elements, but should be treated as one for wrapping, otherwise, steno wrapping may wrap in unwanted places.

## Manipulating elements in `element_collection`

Slices of the class ie `collection[0:4]` is used to obtain `element_collection` of all elements within the collection in the range `start, stop` based on the functional lengths of each element. Use `extract_steno` to use `text` coordinates.

Indexing of class ie `collection[1]` is used to access each element of the collection (returns a `element_collection` class containing only one element). Use `.data` to access the element itself.

`element_collection` methods are heavily biased for `stroke_text` elements relative to other elements.

## Checklist for creating a new element

1.  Determine element functional length
2.  Add any new attributes, check if ODF spec has corresponding equivalent, and use same names if possible
3.  Create 
    1. text representation and
    2. letter to use in steno display
4.  Check if RTF spec or RTF/CRE spec has corresponding equivalent, then create formatted string by overriding, otherwise, just simple text
5.  Create ODF element by overriding, otherwise just simple text
6.  Determine if element needs updating methods or not.
7.  Add to `element_factory` so able to generate element
8.  Create `QUndoCommand` if necessary, and add to `element_action` generator
9.  Create GUI/shortcuts/functions for insertion

## Element Classes

```{eval-rst}
.. automodule:: steno_objects
    :members:
    :show-inheritance:
    :member-order: bysource
    :special-members: __len__, __add__, __radd__, __getitem__, __repr__, __str__
```

