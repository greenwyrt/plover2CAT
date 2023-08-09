import re
import textwrap
from datetime import datetime
from collections import UserList, UserString
from copy import deepcopy
from itertools import accumulate
from bisect import bisect_left, bisect
from plover_cat.helpers import pixel_to_in, write_command
from plover_cat.constants import user_field_dict
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QImage, QImageReader
from odf.teletype import addTextToElement
from odf.text import P, UserFieldDecls, UserFieldDecl, UserFieldGet, UserIndexMarkStart, UserIndexMarkEnd
from odf.draw import Frame, TextBox, Image

_whitespace = '\u2029\t\n\x0b\x0c\r '
whitespace = r'[%s]' % re.escape(_whitespace)
wordsep_simple_re = re.compile(r'(%s+)' % whitespace)

# display letters: s for stroke, t for text, i for image, 
# sa for auto, c for conflict, f for field
# x for "index"/references, e for exhibit

class text_element(UserString):
    """
    base class, only text
    """
    def __init__(self, text = "", time = None):
        super().__init__(text)
        self.element = "text"
        self.time = time or datetime.now().isoformat("T", "milliseconds")
    def __len__(self):
        return(len(self.data))
    def split(self):
        if self.length() > 1:
            chunks = wordsep_simple_re.split(self.data)
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
    def __getitem__(self, key):
        class_dict = deepcopy(self.__dict__)
        class_dict["data"] = self.data[key]
        new_element = self.__class__()
        new_element.from_dict(class_dict)
        return(new_element)
    def __repr__(self):
        items = ("%s = %r" % (k, v) for k, v in self.__dict__.items())
        return("{name}({args})".format(name = self.__class__.__name__, args = ", ".join(items)))
    def length(self):
        return(len(self.data))
    def from_dict(self, dictionary):
        for k, v in dictionary.items():
            setattr(self, k, v)
    def to_display(self):
        return("\U0001F163\n\n%s" % self.to_text())
    def to_json(self):
        return(self.__dict__)
    def to_text(self):
        return(self.data)
    def to_rtf(self):
        time_string = datetime.strptime(self.time, "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')      
        string = write_command("cxt", time_string + ":00", visible = False, group = True) + write_command("cxs", "", visible = False, group = True) + self.to_text()
        return(string)
    def to_odt(self, paragraph, document):
        addTextToElement(paragraph, self.to_text())
    def replace_initial_tab(self, expand = "    "):
        if "\t" in self.data:
            self.data = self.data.replace("\t", expand, 1)
            return True
        else:
            return None

class dummy_element(text_element):
    """
    Used for testing
    """
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.element = "dummy"
    def length(self):
        return(1)

class stroke_text(text_element):
    """
    custom stroke class with timestamps and stroke
    """
    def __init__(self, stroke = "", audiotime = "", **kargs):
        super().__init__(**kargs)
        self.element = "stroke"
        self.stroke = stroke
        self.audiotime = audiotime
    def to_rtf(self):
        time_string = datetime.strptime(self.time, "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')      
        string = write_command("cxt", time_string + ":00", visible = False, group = True) + write_command("cxs", self.stroke, visible = False, group = True) + self.data
        return(string)
    def to_display(self):
        return("\U0001F162\n%s\n%s" % (self.stroke, self.data))

class image_text(text_element):
    """
    custom equivalent of qtextimageformat
    """
    def __init__(self, path = None, width = None, height = None, caption = None, **kargs):
        super().__init__(**kargs)
        self.data = "\ufffc"
        self.element = "image"
        self.path = path
        self.width = width
        self.height = height
    def length(self):
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
    def __init__(self, name = None, user_dict = user_field_dict, **kargs):
        super().__init__(**kargs)
        self.element = "field"
        self.name = name
        self.user_dict = user_dict
    def length(self):
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
    """use for text such as Q\t, ie set directly for question style"""
    def __init__(self, prefix = "", suffix = "", **kargs):
        super().__init__(**kargs)
        self.element = "automatic"
        self.prefix = prefix
        self.suffix = suffix
    def __len__(self):
        return(len(self.to_text()))
    def to_text(self):
        return(self.prefix + self.data + self.suffix)
    def length(self):
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
    # need for resolving with imports from rtf
    def __init__(self, choices = None, **kargs):
        super().__init__(**kargs)
        self.choices = choices

class index_text(text_element):
    """
    text element that holds exhibit
    """
    def __init__(self, prefix = "Exhibit", indexname = 0, description = "", hidden = True, **kargs):
        super().__init__(**kargs)
        self.element = "index"
        # indexname and data ("text") are identifiers, not allowed to change
        self.indexname = indexname
        self.prefix = prefix
        self.description = description
        self.hidden = hidden
    def __len__(self):
        return(len(self.to_text()))
    def length(self):
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
    def __init__(self, **kargs):
        super().__init__(**kargs)
        self.element = "redacted"
    def to_display(self):
        return("\U0001F161\n\n%s" % self.data)
    def to_text(self):
        return("\u2588" * len(self.data))

def translate_coords(len1, len2, pos):
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
    def gen_element(self, element_dict, user_field_dict = user_field_dict):
        # default is always a text element
        element = text_element()
        if element_dict["element"] == "stroke":
            element = stroke_text()
        elif element_dict["element"] == "dummy":
            element = dummy_element()
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
    def __init__(self, data = None):
        # force element into list if not list
        if isinstance(data, list):
            super().__init__(data)
        elif not data:
            super().__init__([])
        else:
            super().__init__([data])
    def __str__(self):
        # string representation of all elements in container
        string = [i.to_text() for i in self.data]
        return("".join(string))
    def lengths(self):
        lengths = [i.length() for i in self.data]
        return(lengths)
    def lens(self):
        lens = [len(i) for i in self.data]
        return(lens)
    def __len__(self):
        return(sum(self.lens()))
    def __getitem__(self, key):
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
        return(len(self.data))
    def to_json(self):
        return([i.to_json() for i in self.data])
    def to_text(self):
        text = [i.to_text() for i in self.data]
        return("".join(text))
    def to_rtf(self):
        col_string = "".join([i.to_rtf() for i in self.data])
        return(col_string)
    def to_odt(self, paragraph, document):
        for i in self.data:
            i.to_odt(paragraph, document)
    def to_display(self):
        return([el.to_display() for el in self.data])
    def remove(self, start, end):
        new_data = []
        first = self.__getitem__(slice(0, start)).data
        new_data.extend(first)
        second = self.__getitem__(slice(end, None)).data
        new_data.extend(second)
        del_data = self.__getitem__(slice(start, end))
        self.data = new_data
        return(del_data)
    def insert(self, i, item):
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
        return(self.data[0].data.startswith(char))
    def ends_with(self, char):
        return(self.data[-1].data.endswith(char))
    def starts_with_element(self, element_type):
        if not self.data:
            return False
        if self.data[0].element == element_type:
            return True
        else:
            return False
    def ends_with_element(self, element_type):
        if self.data[-1].element == element_type:
            return True
        else:
            return False
    def remove_end(self, char = "\n"):
        if self.data[-1].data == char:
            del self.data[-1]
        elif self.data[-1].data.endswith(char):
            self.data[-1].data = self.data[-1].data.rstrip(char) 
    def remove_begin(self, char):
        if self.data[0].data == char:
            del self.data[0]
        elif self.data[0].data.startswith(char):
            self.data[0].data = self.data[0].data.lstrip(char)
    def add_begin(self, char = " "):
        self.data[0].data = char + self.data[0].data
    def add_end(self, char = " "):
        self.data[-1].data = self.data[-1].data + char
    def stroke_count(self):
        # for RTF, maybe has uses elsewhere
        return(sum([el.stroke.count("/") + 1 for el in self.data if el.element == "stroke"]))
    def search_strokes(self, query):
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
        text = "".join([el.to_text() for el in self.data])
        res = re.finditer(re.escape(query), text)
        return(res)
    def collection_time(self, reverse = False):
        times = [el.time for el in self.data]
        return(sorted(times, reverse = reverse)[0])
    def audio_time(self, reverse = False):
        times = [el.audiotime for el in self.data if el.element == "stroke" and el.audiotime != ""]
        if times:
            return(sorted(times, reverse = reverse)[0])
        else:
            return None
    def replace_initial_tab(self, tab_replace = "    "):
        track_len = 3
        for el in self.data:
            if "\t" in el.data[0:track_len]:
                res = el.replace_initial_tab(tab_replace)
                if res:
                    break
            track_len -= len(el)
            if track_len < 0:
                break
         
# stroke_data = [text_element(text = "ABC"), stroke_text(stroke = "T-", text = "it "), automatic_text(text = "\n", prefix = "?"), stroke_text(stroke = "EUFS ", text = "I was ")]
# ex_text = exhibit_text(exhibit_id = "first-exhibit", text = "abc\n")
# stroke_data.append(ex_text)

# stroke_collection = element_collection(stroke_data)
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
    def __init__(self, **kargs):
        super().__init__(**kargs)

    def _split(self, text):
        # override
        text.remove_end()
        chunks = []
        for el in text.data:
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