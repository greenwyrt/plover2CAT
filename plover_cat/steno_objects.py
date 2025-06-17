import re
import textwrap
from datetime import datetime
from collections import UserList, UserString
from copy import deepcopy
from itertools import accumulate
from bisect import bisect_left, bisect
from plover_cat.helpers import pixel_to_in, write_command
from plover_cat.constants import user_field_dict
from PySide6.QtCore import QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QImage, QImageReader
from odf.teletype import addTextToElement
from odf.text import P, UserFieldDecls, UserFieldDecl, UserFieldGet, UserIndexMarkStart, UserIndexMarkEnd
from odf.draw import Frame, TextBox, Image

_whitespace = '\u2029\t\n\x0b\x0c\r '
whitespace = r'[%s]' % re.escape(_whitespace)
wordsep_simple_re = re.compile(r'(%s+)' % whitespace)

class text_element(UserString):
    """The base text element used in editor.

    :param text: string that can be set
    :type text: str
    :param time: time element is created in ISO milliseconds format
    :type time: str
    """
    def __init__(self, text = "", time = None):
        super().__init__(text)
        self.element = "text"
        """type of element, ``text``"""
        self.time = time or datetime.now().isoformat("T", "milliseconds")
    def __len__(self):
        """return length of string"""
        return(len(self.data))
    def split(self):
        """Splits text string on whitespace (re from textwrapper).

        :return: s list of elements containing each text piece separately,
            but same otherwise as original
        :rtype: list
        """
        if self.length() > 1:
            chunks = [c for c in wordsep_simple_re.split(self.data) if c]
            list_chunks = []
            for c in chunks:
                class_dict = deepcopy(self.__dict__)
                class_dict["data"] = c
                new_element = self.__class__()
                new_element.from_dict(class_dict)
                list_chunks.append(new_element)
            return(list_chunks)
        else:
            class_dict = deepcopy(self.__dict__)
            new_element = self.__class__()
            new_element.from_dict(class_dict)
            return([new_element])            
    def __iter__(self):
        """Return element in list length one for iteration. 
        """
        return(iter([self]))
    def __add__(self, other):
        """Adds together text, and updates time from other.
        
        :param other: any type of element
        :type other: ``text_element``
        :return: ``text_element`` object with updated attributes
        :rtype: ``text_element``
        :raise NotImplemented: if type of ``other`` not ``text_element``         
        """
        if type(other) == type(self):
            data = self.data + other.data
            time = other.time
            return(self.__class__(text = data, time = time))
        else:
            return NotImplemented
    def __radd__(self, other):
        """Override __radd__ from ``Userstring`` so inherited classes can override.
        
        :raises NotImplemented: __radd__ should not be needed with purely ``text_element`` objects
        """
        return NotImplemented
    def __getitem__(self, key):
        """Get from class dict based on key.
        
        :param key: key
        :return: returns new instance of class after deepcopy
        """
        class_dict = deepcopy(self.__dict__)
        class_dict["data"] = self.data[key]
        new_element = self.__class__()
        new_element.from_dict(class_dict)
        return(new_element)
    def __repr__(self):
        """Return representation as ``dict``."""
        items = ("%s = %r" % (k, v) for k, v in self.__dict__.items())
        return("{name}({args})".format(name = self.__class__.__name__, args = ", ".join(items)))
    def length(self):
        """Return functional length.
        
        :return: functional length of element, length of text string
        :rtype: int
        """
        return(len(self.data))
    def from_dict(self, dictionary):
        """Populate class using a dict."""
        for k, v in dictionary.items():
            setattr(self, k, v)
    def to_display(self):
        """Formatted string for display in GUI.

        Should be a string for three lines, 1) icon letter, 2) element data, if any, 3) text
        """
        return("\U0001F163\n\n%s" % self.to_text())
    def to_json(self):
        """Return dict of attributes."""
        return(self.__dict__)
    def to_text(self):
        """Return "text" representation as imagined for ``QTextEdit``."""
        return(self.data)
    def to_rtf(self):
        """Return string representation with control groups from RTF/CRE spec as necessary."""
        time_string = datetime.strptime(self.time, "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')      
        string = write_command("cxt", time_string + ":00", visible = False, group = True) + write_command("cxs", "", visible = False, group = True) + self.to_text()
        return(string)
    def to_odt(self, paragraph, document):
        """Populate ODF paragraph element with instance text.
        
        :param paragraph: odfpy paragraph element
        :param document: odfpy document that the paragraph (will) belongs to
        """
        # if there is style highlighting on element level
        # need to general styled text here and add style to document
        addTextToElement(paragraph, self.to_text())
    def replace_initial_tab(self, expand = "    "):
        """Replace first tab in string.
        
        :param expand: string to replace tab with, default four spaces
        :type expand: str
        """
        if "\t" in self.data:
            self.data = self.data.replace("\t", expand, 1)
            return True
        else:
            return None

class dummy_element(text_element):
    """Dummy element used for testing.
    """
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.element = "dummy"
        """type of element, ```dummy```"""
    def length(self):
        return(1)

class stroke_text(text_element):
    """Stroke element used in editor.

    :param stroke: steno outline, separated by slashes
    :type stroke: str
    :param audiotime: time of media at time of stroke
    :type audiotime: str

    """
    def __init__(self, stroke = "", audiotime = "", **kargs):
        super().__init__(**kargs)
        self.element = "stroke"
        """Type of element, ``stroke``."""
        self.stroke = stroke
        self.audiotime = audiotime
    def __add__(self, other):
        """Adds together stroke elements or stroke and text elements.
        Will only combine elements but not across word boundaries (spaces), 
        can accept `stroke_text` and `text_element` but not others while updating
        necessary attributes.

        :param other: ``stroke_element`` or ``text_element``
        :type other: ``stroke_element`` or ``text_element``
        :return: ``stroke_text`` object with updated attributes
        :rtype: ``stroke_text``
        :raise TypeError: if type of ``other`` not correct 
        """
        if self.data.endswith(" ") or other.data.startswith(" "):
            raise ValueError("Elements should not be combined across word boundaries")
        if type(other) == type(self):
            data = self.data + other.data
            time = other.time
            stroke = self.stroke + "/" + other.stroke
            audiotime = other.audiotime
            return(self.__class__(stroke = stroke, time = time, text = data, audiotime = audiotime))
        elif type(other) == text_element:
            data = self.data + other.data
            time = other.time
            stroke = self.stroke
            audiotime = self.audiotime
            return(self.__class__(stroke = stroke, time = time, text = data, audiotime = audiotime))            
        else:
            raise TypeError("Stroke elements can only combine with other stroke or text elements.")
    def __radd__(self, other):
        """Add together elements.

        :param other: ``text_element`` object
        :return: ``stroke_text`` object with updated attributes
        :rtype: ``stroke_text``
        :raise NotImplemented: if type of ``other`` is not ``text_element``
        :raise ValueError: if trying to combine across word boundaries        
        """
        if self.data.startswith(" ") or other.data.endswith(" "):
            raise ValueError("Elements should not be combined across word boundaries")        
        if isinstance(other, text_element):
            data = other.data + self.data
            time = self.time
            stroke = self.stroke
            audiotime = self.audiotime
            return(self.__class__(stroke = stroke, time = time, text = data, audiotime = audiotime))
        else:
            return NotImplemented
            # raise TypeError("Stroke elements can only combine with other stroke or text elements.")
    def to_rtf(self):
        time_string = datetime.strptime(self.time, "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')      
        string = write_command("cxt", time_string + ":00", visible = False, group = True) + write_command("cxs", self.stroke, visible = False, group = True) + self.data
        return(string)
    def to_display(self):
        return("\U0001F162\n%s\n%s" % (self.stroke, self.data))

class image_text(text_element):
    """Image element used in editor.

    :param path: path to image
    :type path: str or `Path`
    :param width: pixel width of image
    :type width: int
    :param height: pixel height of image
    :type height: int
    """
    def __init__(self, path = None, width = None, height = None, **kargs):
        super().__init__(**kargs)
        self.data = "\ufffc"
        """Representation of image when image cannot be rendered."""
        self.element = "image"
        """Type of element, ``image``."""
        self.path = path
        self.width = width
        self.height = height
    def __add__(self, other):
        """Addition of elements to image is not allowed.
        
        :raise NotImplemented: images cannot add or be added to other elements.
        """
        return NotImplemented
        # raise NotImplementedError("Cannot add on image element.")
    def length(self):
        """Return functional length of ``image_text``, 1.

        :return: 1
        :rtype: int
        """
        return(1)
    def to_display(self):
        return("\U0001F158\n%s\n " % self.path)
    def to_rtf(self):
        image = QImage(QImageReader(self.path).read())
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        hex_string = ba.toHex()
        string = (write_command("pngblip") + write_command("picw", value = image.width())
                 + write_command("pich", value = image.height()) + write_command("picwgoal", value = image.width() * 15)
                 + write_command("pichgoal", value = image.height() * 15))
        string = write_command("pict", hex_string.data().decode(), value=string, group = True)
        return(string)
    def to_odt(self, paragraph, document):
        width_in = "{0}in".format(pixel_to_in(self.width))
        height_in = "{0}in".format(pixel_to_in(self.height))
        image_frame = Frame(attributes = {"stylename": "Graphics", "anchortype": "as-char", "width": width_in, "height": height_in})
        image_ref = document.addPicture(self.path)
        image_frame.addElement(Image(href = image_ref))
        paragraph.addElement(image_frame)

class text_field(text_element):
    """Field element to use in editor.

    :param name: name of field
    :type name: str
    :param user_dict: transcript field dict, uses default ``user_field_dict`` if not supplied
    :type user_dict: dict
    """
    def __init__(self, name = None, user_dict = user_field_dict, **kargs):
        super().__init__(**kargs)
        self.element = "field"
        """Type of element, ``field``"""
        self.name = name
        self.user_dict = user_dict
        self.update()
    def __add__(self, other):
        """No element can be added. Force use of ``__radd__``.

        :raise NotImplemented: addition not allowed 
        """
        return NotImplemented
        # raise NotImplementedError("Cannot add on text field element.")
    def length(self):
        """Return functional length, 1

        :return: 1
        :rtype: int
        """
        return(1)
    def to_json(self):
        new = {k: v for k, v in self.__dict__.items() if k != "user_dict"}
        return(new)        
    def to_display(self):
        self.update()
        return("\U0001F155\n \n%s" % self.data)
    def to_text(self):
        self.update()
        return(self.data)
    def update(self):
        """Update data for display. Check the ``user_dict`` and assigns value to ``data``, 
        "updating" if the value in the dict for the ``name`` has been changed.
        The ``user_field_dict`` by default uses the global `user_field_dict` object.
        Need to specify if a different dict is to be used.
        """
        if self.name in self.user_dict:
            self.data = self.user_dict[self.name]
        else:
            self.data = "{%s}" % str(self.name)
    def to_rtf(self):
        self.update()
        rtf_string = write_command("fldinst", "DOCVARIABLE %s" % self.name, visible=False, group=True)
        rtf_string = rtf_string + write_command("fldrslt", self.data)
        rtf_string = write_command("fldlock", rtf_string, group = True)
        return(write_command("field", rtf_string))
    def to_odt(self, paragraph, document):
        self.update()
        # move this out to actual function, since this is setting document var
        user_declares = document.text.getElementsByType(UserFieldDecls)
        if user_declares:
            field_names = [i.getAttribute("name") for i in document.text.getElementsByType(UserFieldDecl)]
            if not self.name in field_names:
                user_declares = document.text.getElementsByType(UserFieldDecls)[0]
                user_dec = UserFieldDecl(name = self.name, stringvalue = self.data, valuetype = "string")
                user_declares.addElement(user_dec)                
        else:
            user_declares = UserFieldDecls()
            user_dec = UserFieldDecl(name = self.name, stringvalue = self.data, valuetype = "string")
            user_declares.addElement(user_dec)
            document.text.addElement(user_declares)
        user_field = UserFieldGet(name = self.name)
        user_field.addText(self.data)
        paragraph.addElement(user_field)

class automatic_text(stroke_text):
    """Automatic text element for editor, text added by editor, not user.
    
    Use for text such as Q\t, ie set directly for question style.
    
    :param prefix: text to appear before string
    :type prefix: str
    :param suffix: text to appear after string
    :type suffix: str
    """
    def __init__(self, prefix = "", suffix = "", **kargs):
        super().__init__(**kargs)
        self.element = "automatic"
        """Type of element, ``automatic``"""
        self.prefix = prefix
        self.suffix = suffix
    def __add__(self, other):
        """No element can be added. Force use of ``__radd__``.

        :raise NotImplemented: addition not allowed.
        """
        return NotImplemented
    # raise NotImplementedError("Cannot add on automatic text element.")
    def __radd__(self, other):
        """No element can be added.

        :raise NotImplemented: ``__radd__`` not allowed.
        """
        return NotImplemented
    def __len__(self):
        """Return length of prefix + text + suffix."""
        return(len(self.to_text()))
    def to_text(self):
        return(self.prefix + self.data + self.suffix)
    def length(self):
        """Return length of data, compare to ``__len__()``."""
        return(len(self.data))
    def to_rtf(self):
        string = ""
        if self.prefix:
            string = string + write_command("cxa",  self.prefix, visible = False, group = True)
        string = string + write_command("cxt", self.time + ":00", visible = False, group = True) + write_command("cxs", self.stroke, visible = False, group = True) + self.data
        if self.suffix:
            string = string + write_command("cxa",  self.suffix, visible = False, group = True)
        return(string)
    def to_display(self):
        return(f"\U0001F162 \U0001F150\n{self.stroke}\n{self.to_text()}")

class conflict_text(stroke_text):
    """Not yet implemented"""
    # need for resolving with imports from rtf
    def __init__(self, choices = None, **kargs):
        super().__init__(**kargs)
        self.choices = choices

class index_text(text_element):
    """Index entry element for editor.

    :param prefix: prefix to place before "number"
    :type prefix: str
    :param indexname: index that index entry belongs to
    :type indexname: int
    :param description: index entry description
    :type description: str
    :param hidden: whether description should be shown in editor or hidden
    :type hidden: bool
    """
    def __init__(self, prefix = "Exhibit", indexname = 0, description = "", hidden = True, **kargs):
        super().__init__(**kargs)
        self.element = "index"
        """Type of element, ``index``"""
        # indexname and data ("text") are identifiers, not allowed to change
        self.indexname = indexname
        self.prefix = prefix
        self.description = description
        self.hidden = hidden
    def __add__(self, other):
        """No element can be added. Force use of ``__radd__``.

        :raise NotImplemented: addition not allowed.
        """        
        return NotImplemented
        # raise NotImplementedError("Cannot add on index text element.")
    def __len__(self):
        """Return length of index entry text, may or may not include description."""
        return(len(self.to_text()))
    def length(self):
        """Return functional length, 1

        :return: 1
        :rtype: int
        """
        return(1)
    def to_text(self):
        if self.hidden:
            return(f"{self.prefix}\u0020{self.data}")
        else:
            return(f"{self.prefix}\u0020{self.data}{self.description}")
    def to_display(self):
        return(f"\U0001F154\n\n{self.to_text()}")
    def to_odt(self, paragraph, document):
        # while first instinct is to use self.time, problem with copied steno if index
        id_time = str(datetime.now().timestamp())
        index_start = UserIndexMarkStart(id = id_time, indexname = self.indexname)
        index_end = UserIndexMarkEnd(id = id_time)
        paragraph.addElement(index_start)
        addTextToElement(paragraph, self.to_text())
        paragraph.addElement(index_end)
    def to_rtf(self):
        # Exhibit 1{\xe\cxinum1\v Exhibit 1:  A knife}
        # {\xe{\*\cxexnum 1}Exhibit 1:  A knife}
        string = write_command("cxinum", value = self.indexname)
        if self.hidden:
            string = string + write_command("v")
        string = write_command("cxexnum", self.data, visible = False, group = True) + string
        string = write_command("xe", text = f"{self.prefix}\u0020{self.data}{self.description}", value = string, group = True)
        if self.hidden:
            string = self.to_text() + string
        return(string)

class redact_text(text_element):
    """Not yet implemented"""
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.element = "redacted"
    def to_display(self):
        return("\U0001F161\n\n%s" % self.data)
    def to_text(self):
        return("\u2588" * len(self.data))

def translate_coords(len1, len2, pos):
    """Translate position from one sequence of cumulative lengths to another.
    
    :param len1: cumulative text lengths of elements (ie in display of editor)
    :type len1: list[int]
    :param len2: cumulative functional lengths of elements, can be 1 or other int
    :type len2: list[int]
    :param pos: position from first sequence to translate
    :type pos: int
    
    :return: position in second sequence
    :rtype: int
    """
    pos_index = bisect_left(len1, pos)
    if pos_index == 0:
        remainder = pos     
    elif pos in len1:
        remainder = 0
    else:
        remainder = pos - len1[pos_index - 1]
    if remainder == 0:
        steno_pos = len2[pos_index]
    else:
        if remainder > (len2[pos_index] - len2[pos_index - 1]):
            steno_pos = len2[pos_index - 1] + (len2[pos_index] - len2[pos_index - 1])
        else:
            steno_pos = len2[pos_index - 1] + remainder  
    return(steno_pos) 

def backtrack_coord(pos, backspace, text_len, func_len):
    """Return position after backspace, accounting for functional length of elements.

    :param pos: initial position in text
    :type pos: int
    :param backspace: hypothetical backspaces to mock
    :type backspace: int
    :param text_len: text lengths of elements
    :type text_len: list[int]
    :param func_len: functional lengths of elements
    :type func_len: list[int]

    :return: position after hypothetical backspaces, may be negative
        if more ``backspaces`` than length
    :rtype: int
    """
    # guard against that edgecase
    if backspace == 0:
        return(pos)
    cum_text_len = list(accumulate(text_len))
    cum_text_len.insert(0, 0)
    cum_func_len = list(accumulate(func_len))
    cum_func_len.insert(0, 0)
    func_pos = translate_coords(cum_text_len, cum_func_len, pos)
    ending_func_pos = func_pos - backspace
    if ending_func_pos < 0:
        # if more backspaces than exists in collection
        return(ending_func_pos)
    cum_func_index = bisect_left(cum_func_len, ending_func_pos)
    if cum_func_index == 0:
        return(0)
    elif ending_func_pos in cum_func_len:
        return(cum_text_len[cum_func_index])
    else:
        return(cum_text_len[cum_func_index - 1] +  ending_func_pos - cum_func_len[cum_func_index - 1])

# text_len = [4, 6, 4, 6, 5, 5]
# func_len = [4, 1, 4, 1, 5, 5]
# pos = 25
# backspace = 5
# backtrack_coord(pos, backspace, text_len, func_len)
# backtrack_coord(24, backspace, text_len, func_len)
# text_len = [4, 3, 3, 5]
# func_len = [4, 3, 1, 5]
# pos = 10
# backspace = 1
# backtrack_coord(pos, backspace, text_len, func_len)

class element_factory:
    """Factory for creating elements from data dict"""
    def gen_element(self, element_dict, user_field_dict = user_field_dict):
        """Return element based on type.
        
        :param element_dict: dict of element, likely from dict representation
        :type element_dict: dict
        :param user_field_dict: user field data
        :type user_field_dict: dict
        :return: element
        :rtype: `text_element` or subclass
        """
        # default is always a text element
        element = text_element()
        if element_dict["element"] == "stroke":
            element = stroke_text()
        # elif element_dict["element"] == "dummy":
        #     element = dummy_element()
        elif element_dict["element"] == "image":
            element = image_text()
        elif element_dict["element"] == "field":
            element = text_field(user_dict = user_field_dict)
        elif element_dict["element"] == "automatic":
            element = automatic_text()
        elif element_dict["element"] == "index":
            element = index_text()
        element.from_dict(element_dict)
        return(element)

class element_collection(UserList):
    """Container for holding elements in list."""
    def __init__(self, data = None):
        # force element into list if not list
        if isinstance(data, list):
            super().__init__(data)
        elif not data:
            super().__init__([])
        else:
            super().__init__([data])
    def __iter__(self):
        return(iter(self.data))
    def __str__(self):
        """Return string representation of all elements in container."""
        string = [i.to_text() for i in self.data]
        return("".join(string))
    def lengths(self):
        """Return list of functional lengths for each element."""
        lengths = [i.length() for i in self.data]
        return(lengths)
    def lens(self):
        """Return list of "text" lengths for each element."""
        lens = [len(i) for i in self.data]
        return(lens)
    def __len__(self):
        """Returns sum of `len` for each element."""
        return(sum(self.lens()))
    def __getitem__(self, key):
        """Return `element_collection` instance with copy of element(s) based on key."""
        if isinstance(key, slice):
            el_lengths = list(accumulate(self.lengths()))
            start = key.start
            if not start:
                start = 0
            end = key.stop
            el_part = self.__class__()
            if end == 0:
                return(el_part)
            if not self.data:
                return(el_part)
            if not end:
                end = el_lengths[-1]
            if start < 0 or end < 0:
                raise ValueError("negative slices not supported")            
            if end > max(el_lengths):
                raise IndexError('list index out of range')
            if start == el_lengths[-1]:
                return(el_part)
            first_whole = bisect_left(el_lengths, start)
            if first_whole == 0:
                first_remain = start
            else:
                first_remain = start - el_lengths[(first_whole - 1)]
            last_whole = bisect_left(el_lengths, end)
            if last_whole == 0:
                last_remain = end
            else:
                last_remain = end - el_lengths[(last_whole - 1)]
            # special case where first and last are within same element
            data = deepcopy(self.data)
            if first_whole == last_whole:
                el_part.append(data[last_whole][first_remain:last_remain])
                return(el_part)
            if not start in el_lengths:
                el_part.append(data[first_whole][first_remain:])
            if (first_whole + 1) != last_whole:
                for i in data[(first_whole + 1): last_whole]:
                    el_part.append(i)
            if not end in el_lengths:
                el_part.append(data[last_whole][:last_remain])
            else:
                el_part.append(data[last_whole])
            return(el_part)
        else:
            return(self.__class__(deepcopy(self.data[key])))
        # always return element collection, even when not a slice
    def element_count(self):
        """Return number of elements in collection, ``len`` of a list."""
        return(len(self.data))
    def to_json(self):
        """Return list of serialized ``dict`` objects."""
        return([i.to_json() for i in self.data])
    def to_text(self):
        """Return text string combining all elements."""
        text = [i.to_text() for i in self.data]
        return("".join(text))
    def to_rtf(self):
        """Return string containing RTF representations of elements."""
        col_string = "".join([i.to_rtf() for i in self.data])
        return(col_string)
    def to_odt(self, paragraph, document):
        """Add each element to paragraph in ODF document"""
        for i in self.data:
            i.to_odt(paragraph, document)
    def to_display(self):
        """Return list of display strings for elements"""
        return([el.to_display() for el in self.data])
    def to_strokes(self):
        """Return strin with all strokes"""
        el_strokes = [el.stroke for el in self.data if el.element == "stroke"]
        return("/".join(el_strokes))
    def remove(self, start, end):
        """Remove elements based on specified functional position start/stop.

        :param int start: start position for remove
        :param int end: end position for remove
        :return: removed elements
        :rtype: ``element_collection``
        """
        new_data = []
        first = self.__getitem__(slice(0, start)).data
        new_data.extend(first)
        second = self.__getitem__(slice(end, None)).data
        new_data.extend(second)
        del_data = self.__getitem__(slice(start, end))
        self.data = new_data
        return(del_data)
    def insert(self, i, item):
        """Insert based on functional position.
        :param int i: position
        :param item: data to be inserted
        :return: item
        """
        new_data = []
        first = self.__getitem__(slice(0, i))
        second = self.__getitem__(slice(i, None))
        new_data.extend(first.data)
        if isinstance(item, UserList):
            new_data.extend(item.data)
        else:
            new_data.append(item)
        new_data.extend(second.data)
        self.data = new_data
        return(item)
    def stroke_pos_at_pos(self, pos):
        """Returns tuple of text start, stop for element at text ``pos``."""
        lengths = self.lens()
        cum_len = list(accumulate(lengths))
        pos_index = bisect(cum_len, pos)
        # if first, need manual adjustment
        if pos_index == 0:
            start_pos = 0
        else:
            start_pos = cum_len[pos_index - 1]
        # if last, pos_index will cause out of range error, subtract back 
        if pos >= cum_len[-1]:
            pos_index = pos_index - 1
            start_pos = cum_len[pos_index - 1]
        return((start_pos, cum_len[pos_index]))
    def element_pos(self, index):
        """Returns tuple of text start, stop for element at ``index`` in collection."""
        lengths = self.lens()
        cum_len = list(accumulate(lengths))
        if index == 0:
            start_pos = 0
        else:
            start_pos = cum_len[index - 1]
        if index >= len(cum_len):
            index = index - 1
            start_pos = cum_len[index - 1]            
        return((start_pos, cum_len[index]))            
    def remove_steno(self, start, end):
        """Removes elements from `start` to `end` (text) position.
        
        :return: element(s) removed
        :rtype: ``element_collection``
        """
        lens = self.lens()
        cum_len = list(accumulate(lens))
        cum_len.insert(0, 0)
        # print(cum_len)
        lengths = self.lengths()
        cum_lengths = list(accumulate(lengths))
        cum_lengths.insert(0, 0)
        start_pos = translate_coords(cum_len, cum_lengths, start)
        end_pos = translate_coords(cum_len, cum_lengths, end)
        res = self.remove(start_pos, end_pos)
        return(res)
    def extract_steno(self, start, end):
        """Retrieve elements from ``start`` to ``end`` (text) position.

        This does not modify original collection.

        :param int start: starting text position
        :param int end: ending text position
        :return: element(s) between coordinates
        :rtype: ``element_collection``
        """
        lens = self.lens()
        cum_len = list(accumulate(lens))
        cum_len.insert(0, 0)
        # print(cum_len)
        lengths = self.lengths()
        cum_lengths = list(accumulate(lengths))
        cum_lengths.insert(0, 0)
        start_pos = translate_coords(cum_len, cum_lengths, start)
        end_pos = translate_coords(cum_len, cum_lengths, end)
        res = self[start_pos:end_pos]
        return(res)        
    def insert_steno(self, pos, item):
        """Insert at text position.

        This will split an element in collection if needed.

        :param int pos: text position
        :param item: ``element_collection`` or single element
        :return: item
        """
        lens = self.lens()
        cum_len = list(accumulate(lens))
        cum_len.insert(0, 0)
        # print(cum_len)
        lengths = self.lengths()
        cum_lengths = list(accumulate(lengths))
        cum_lengths.insert(0, 0)
        steno_pos = translate_coords(cum_len, cum_lengths, pos)
        res = self.insert(steno_pos, item)
        return(res)
    def starts_with(self, char):
        """Check if text starts with ``char``.

        :param str char: text to check
        :return: ``True`` if collection text does start with ``char``, 
            ``False`` otherwise
        :rtype: bool
        """
        return(self.data[0].data.startswith(char))
    def ends_with(self, char):
        """Check if text ends with ``char``

        :param str char: text to check
        :return: ``True if collection text ends with ``char``,
            ``False`` otherwise
        :rtype: bool
        """
        return(self.data[-1].data.endswith(char))
    def starts_with_element(self, element_type):
        """Check if first element is of type.
        
        :param str element_type: any of the types for ``text_element`` or subclasses
        :return: ``True`` if first element type matches ``element_type``, ``False`` otherwise
        :rtype: bool
        """
        if not self.data:
            return False
        if self.data[0].element == element_type:
            return True
        else:
            return False
    def ends_with_element(self, element_type):
        """Check if last element is of type.
        
        :param str element_type: any of the types for ``text_element`` or subclasses
        :return: ``True`` if last element type matches ``element_type``, ``False`` otherwise
        :rtype: bool
        """
        if self.data[-1].element == element_type:
            return True
        else:
            return False
    def remove_end(self, char = "\n"):
        """Remove ``char`` end of text string for collection.

        This will remove entire element if ``char`` is only text in element.

        :param str char: string to remove, default ``\\n``
        """
        if self.data[-1].data == char:
            del self.data[-1]
        elif self.data[-1].data.endswith(char):
            self.data[-1].data = self.data[-1].data.rstrip(char) 
    def remove_begin(self, char):
        """Remove ``char`` from first element if text starts with ``char``.

        :param str char: string to remove
        """
        if self.data[0].data == char:
            del self.data[0]
        elif self.data[0].data.startswith(char):
            self.data[0].data = self.data[0].data.lstrip(char)
    def add_begin(self, char = " "):
        """Add ``char`` to beginning of first element.
        
        :param str char: string to add, default one space character
        """
        self.data[0].data = char + self.data[0].data
    def add_end(self, char = " "):
        """Add ``char`` to end of last element.
        
        :param str char: string to add, default one space character
        """
        self.data[-1].data = self.data[-1].data + char
    def stroke_count(self):
        """Counts the number of strokes in collection."""
        # for RTF, maybe has uses elsewhere
        return(sum([el.stroke.count("/") + 1 for el in self.data if el.element == "stroke"]))
    def search_strokes(self, query):
        """Return text positions for matches to underlying strokes.

        :param str query: steno outline
        :return: tuple of start and end positions, ``None`` if no match
        """
        stroke_list = [el.stroke if el.element == "stroke" else " " for el in self.data]
        query = query.split("/")
        # must match across strokes, match whole element of stroke
        # cannot match across stroke auto_text stroke
        match = False
        for i, subsets in enumerate(zip(*(stroke_list[i:] for i in range(len(query))))):
            if tuple(query) == subsets:
                match = True
                break
        if not match:
            return None
        start_pos = self.element_pos(i)[0]
        end_pos = self.element_pos(i + len(query))[0]    
        return((start_pos, end_pos))
    def search_text(self, query):
        """Return text positions for matches to text.

        :param str query: search text
        :return: results of ``re.finditer`` search
        """        
        text = "".join([el.to_text() for el in self.data])
        res = re.finditer(re.escape(query), text)
        return(res)
    def collection_time(self, reverse = False):
        """Return earliest/latest timestamp in collection.

        :param bool reverse: ``True`` by default for earliest, 
            ``False`` for latest
        :return: formatted timestamp string
        """
        times = [el.time for el in self.data]
        return(sorted(times, reverse = reverse)[0])
    def audio_time(self, reverse = False):
        """Return earliest/latest audio timestamp in collection.

        :param bool reverse: ``True`` by default for earliest, 
            ``False`` for latest
        :return: formatted timestamp string
        """
        times = [el.audiotime for el in self.data if el.element == "stroke" and el.audiotime != ""]
        if times:
            return(sorted(times, reverse = reverse)[0])
        else:
            return None
    def replace_initial_tab(self, tab_replace = "    "):
        """Replace initial tab in place within collection.

        :param str tab_replace: string to replace tab character with, default four spaces
        """
        track_len = 3
        for el in self.data:
            if "\t" in el.data[0:track_len]:
                res = el.replace_initial_tab(tab_replace)
                if res:
                    break
            track_len -= len(el)
            if track_len < 0:
                break
    def merge_elements(self):
        """Collapse collection elements using ``__add__`` method.
        """
        new_ec = []
        last_el_type = ""
        for ind, el in enumerate(self.data):
            if ind == 0:
                new_ec.append(el)
                continue
            try:
                sum_el = new_ec[-1] + el
                new_ec[-1] = sum_el
            except (TypeError, ValueError, NotImplementedError):
                new_ec.append(el)
        return(self.__class__(new_ec))

# stroke_data = [text_element(text = "ABC"), stroke_text(stroke = "T-", text = "it "), text_element(text = "2 ", time = "2023-08-09T23:02:26.526"), text_element(text = "3 "), stroke_text(stroke = "EUFS ", text = "I was "), stroke_text(stroke = "TAO", text = "too ")]
# ex_text = index_text(description = "index descript", text = "index name")
# stroke_data.append(ex_text)

# stroke_collection = element_collection(stroke_data)
# stroke_collection.merge_elements()
# stroke_collection.replace_initial_tab("  ")
# element_list = stroke_collection.to_json() 
# el_factory = element_factory()
# [el_factory.gen_element(element_dict = i) for i in element_list]
# stroke_collection.search_strokes("T-")
# stroke_collection
# ex_text.data = "oops"
# str(stroke_collection)
# stroke_collection.stroke_pos_at_pos(2)
# stroke_collection.stroke_pos_at_pos(7)
# stroke_collection.stroke_pos_at_pos(15)
# stroke_collection[0]
# stroke_collection[2]
# stroke_collection[6]
# stroke_collection[2:7]
# # stroke_collection.remove(2,7)
# new_stroke_data = [text_element(text = "ABCD"), text_element(text = "123"), text_element(text = "456")]

# stroke_collection.insert(2, new_stroke_data)
# new_stroke_collection = element_collection(new_stroke_data)

# # stroke_collection.insert(5, new_stroke_collection)
# stroke_collection.insert_steno(7, new_stroke_collection)
# str(stroke_collection)

class steno_wrapper(textwrap.TextWrapper):
    """Wrap text, but adapted for elements in ``element_collection``.
    
    :return: a list of lists of elements, not ``element_collection``.
    """
    def __init__(self, **kargs):
        super().__init__(**kargs)

    def _split(self, text):
        # override
        text.remove_end()
        merged = text.merge_elements()
        chunks = []
        for el in merged:
            chunks.extend(el.split())
        return chunks

    def _wrap_chunks(self, chunks):
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        if self.max_lines is not None:
            if self.max_lines > 1:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            if len(indent) + len(self.placeholder.lstrip()) > self.width:
                raise ValueError("placeholder too large for max width")

        chunks.reverse()

        while chunks:
            cur_line = []
            cur_len = 0
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            width = self.width - len(indent)
            # if self.drop_whitespace and chunks[-1].strip() == '' and lines:
            #     del chunks[-1]
            while chunks:
                l = len(chunks[-1])
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l
                else:
                    break
            if chunks and len(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(len, cur_line))

        #     # If the last chunk on this line is all whitespace, drop it.
        #     if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
        #         cur_len -= len(cur_line[-1])
        #         del cur_line[-1]

            if cur_line:
                lines.append(cur_line)
        return lines

    def _split_chunks(self, text):
        return self._split(text)

    def wrap(self, text):
        chunks = self._split_chunks(text)
        return self._wrap_chunks(chunks)

# wrap_text = steno_wrapper(width = 10)
# wrap_text.wrap(stroke_collection)