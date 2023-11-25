import collections
import time
from plover import log
from PyQt5.QtGui import QTextBlockUserData, QTextDocument, QTextCursor, QTextBlock, QImage, QImageReader, QTextImageFormat
from PyQt5.QtCore import QUrl, QVariant
from PyQt5.QtWidgets import QUndoCommand
from datetime import datetime, timezone
from plover_cat.steno_objects import *

class BlockUserData(QTextBlockUserData):
    """Representation of the data for a block, from ninja-ide"""
    def __init__(self):
        QTextBlockUserData.__init__(self)
        self.attrs = collections.defaultdict(str)
        self.attrs["strokes"] = element_collection()
    def get(self, name, default=None):
        return self.attrs.get(name, default)
    def __getitem__(self, name):
        return self.attrs[name]
    def __setitem__(self, name, value):
        self.attrs[name] = value
    def return_all(self):
        return self.attrs
    def __len__(self):
        return len(self.attrs)

def update_user_data(block_dict, key, value = None):
    """Update BlockUserData key with default value (time) if not provided

    Args:
        block_dict: a BlockUserData from a QTextBlock.
        key (str): key to be updated.
        value (str): if None, automatically insert time.
    
    Returns:
        BlockUserData

    """
    old_dict = block_dict.return_all()
    new_dict = BlockUserData()
    for k, v in old_dict.items():
        new_dict[k] = v
    if value is None:
        value = datetime.now().isoformat("T", "milliseconds")
    new_dict[key] = value
    return new_dict 

class element_actions:
    def make_action(self, document, block, position_in_block, element):
        if element.element == "image":
            cmd = image_insert(document, block, position_in_block, element)
        else:
            # treat all "text" elements the same
            cmd = steno_insert(document, block, position_in_block, element)
        return(cmd)

class steno_insert(QUndoCommand):
    """Inserts text and steno data into textblock in textdocument"""
    def __init__(self, cursor, document, block, position_in_block, steno):
        super().__init__()
        self.document = document        
        self.block = block
        self.position_in_block = position_in_block
        self.steno = steno
        self.block_state = 1
        self.cursor = cursor
    def redo(self):
        current_cursor = self.cursor
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        self.block_state = current_block.userState()
        self.document.setTextCursor(current_cursor)
        if current_block.userData():
            block_data = current_block.userData()
        else:
            block_data = BlockUserData()
        log.debug("Insert: Insert text at %s" % str(current_block.position() + self.position_in_block))
        block_data["strokes"].insert_steno(self.position_in_block, self.steno)
        block_data = update_user_data(block_data, "edittime")
        current_block.setUserData(block_data)
        current_cursor.insertText(self.steno.to_text())
        current_block.setUserState(1)
        self.document.setTextCursor(current_cursor)
        log_dict = {"action": "insert", "block": self.block, "position_in_block": self.position_in_block, "steno": self.steno.to_json()}
        log.info(f"Insert: {log_dict}")
        self.setText("Insert: %s" % self.steno.to_text())
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + len(self.steno.to_text().rstrip("\n"))
        current_cursor.setPosition(start_pos)
        current_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        res = block_data["strokes"].remove_steno(self.position_in_block, self.position_in_block + len(self.steno.to_text()))
        block_data = update_user_data(block_data, "edittime")
        current_block.setUserData(block_data)
        current_cursor.removeSelectedText()
        log_dict = {"action": "remove", "block": self.block, "position_in_block": self.position_in_block, "end": self.position_in_block + len(self.steno.to_text())}
        log.info(f"Insert (undo): {log_dict}")
        self.document.setTextCursor(current_cursor)
              
class steno_remove(QUndoCommand):
    """Removes text and steno data from textblock in textdocument"""
    def __init__(self, cursor, document, block, position_in_block, length, steno = ""):
        super().__init__()
        self.document = document
        self.block = block
        self.position_in_block = position_in_block
        self.length = length
        self.steno = steno
        self.block_state = 1
        self.cursor = cursor
    def redo(self):
        current_cursor = self.cursor
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        current_cursor.setPosition(start_pos)
        block_data = current_block.userData()
        self.block_state = current_block.userState()
        self.steno = block_data["strokes"].remove_steno(self.position_in_block, self.position_in_block + self.length)
        block_data = update_user_data(block_data, "edittime")
        current_cursor.setPosition(start_pos + len(self.steno), QTextCursor.KeepAnchor)
        self.document.setTextCursor(current_cursor)        
        current_block.setUserData(block_data)
        current_cursor.removeSelectedText()
        current_block.setUserState(1)
        self.document.setTextCursor(current_cursor)
        log_dict = {"action": "remove", "block": self.block, "position_in_block": self.position_in_block, "end": self.position_in_block + self.length}
        log.info(f"Remove: {log_dict}")
        self.setText("Remove: %d backspace(s)" % len(self.steno))
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + self.length
        current_cursor.setPosition(start_pos)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        res = block_data["strokes"].insert_steno(self.position_in_block, self.steno)
        block_data = update_user_data(block_data, "edittime")
        current_block.setUserData(block_data)
        current_cursor.insertText(self.steno.to_text())
        log_dict = {"action": "insert", "block": self.block, "position_in_block": self.position_in_block, "steno": self.steno.to_json()}
        log.info(f"Remove (undo): {log_dict}")
        self.document.setTextCursor(current_cursor)

class image_insert(QUndoCommand):
    """Insert image into text block"""
    def __init__(self, document, block, position_in_block, image_element):
        super().__init__()
        self.document = document        
        self.block = block
        self.position_in_block = position_in_block
        self.image_element = image_element
        self.block_state = 1
    def redo(self):
        # prep image for qt insert
        imageUri = QUrl("file://{0}".format(self.image_element.path))
        image = QImage(QImageReader(self.image_element.path).read())
        self.document.document().addResource(
            QTextDocument.ImageResource,
            imageUri,
            QVariant(image)
        )
        imageFormat = QTextImageFormat()
        imageFormat.setWidth(image.width())
        imageFormat.setHeight(image.height())
        imageFormat.setName(imageUri.toString())
        self.image_element.width = image.width()
        self.image_element.height = image.height()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_block.userData()["strokes"].insert_steno(self.position_in_block, self.image_element)
        self.block_state = current_block.userState()
        current_cursor = self.document.textCursor()
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        log_dict = {"action": "insert", "block": self.block, "position_in_block": self.position_in_block, "steno": self.image_element.to_json()}
        log.info(f"Insert: {log_dict}")
        current_cursor.insertImage(imageFormat)
        current_block.setUserState(1)
        self.setText("Insert: image object")
        self.document.setTextCursor(current_cursor)
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        current_cursor.setPosition(current_block.position() + self.position_in_block + 1, QTextCursor.KeepAnchor)
        current_block.userData()["strokes"].remove_steno(self.position_in_block, self.position_in_block + 1)
        current_cursor.removeSelectedText()
        log_dict = {"action": "remove", "block": self.block, "position_in_block": self.position_in_block, "end": self.position_in_block + 1}
        log.info(f"Insert image (undo): {log_dict}")        
        self.document.setTextCursor(current_cursor)

# split_steno and merge_steno are using cursor movements repeatedly rather than insertText and removeSelectedText
# otherwise image objects are replaced by OBJ chars

class split_steno_par(QUndoCommand):
    """ Splits paragraphs at position in block, and puts steno properly with new textblock """
    def __init__(self, cursor, document, block, position_in_block, space_placement, new_line_stroke, remove_space = True):
        super().__init__()
        self.block = block
        self.position_in_block = position_in_block
        self.document = document
        self.strokes = []
        self.remove_space = remove_space
        self.space_placement = space_placement
        self.new_line_stroke = automatic_text()
        self.new_line_stroke.from_dict(new_line_stroke.to_json())
        self.block_text = ""
        self.block_data = ""
        self.block_state = 1
        self.cursor = cursor
    def redo(self):
        current_cursor = self.cursor
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        self.block_data = deepcopy(current_block.userData().return_all())
        self.block_text = current_block.text()
        stroke_data = self.block_data["strokes"]
        # first_part = stroke_data.extract_steno(0, self.position_in_block)
        second_part = current_block.userData()["strokes"].remove_steno(self.position_in_block, len(current_block.userData()["strokes"].to_text()))
        first_data = current_block.userData()
        second_data = BlockUserData()
        first_data = update_user_data(first_data, key = "edittime")
        second_data = update_user_data(second_data, key = "edittime")
        if second_part and self.remove_space and self.space_placement == "Before Output":
            if second_part.starts_with(" "):
                log.debug("Split: Stripping space from beginning of second piece")
                second_part.remove_begin(" ")
        log.debug("Split: Appending new line stroke to end of second piece")
        fake_newline_stroke = self.new_line_stroke
        current_block.userData()["strokes"].append(deepcopy(fake_newline_stroke))
        # this is important on last segment that has audioendtime
        if first_data["audioendtime"]:
            second_data = update_user_data(second_data, key = "audioendtime", value = first_data["audioendtime"])
            first_data = update_user_data(first_data, key = "audioendtime", value = "")
        # check the strokes if there is an audio time associated with stroke
        # use first stroke that has an audio time
        focal_stroke = next((stroke for stroke in second_part if isinstance(stroke, stroke_text) and stroke.audiotime), None) 
        if focal_stroke:
            second_data = update_user_data(second_data, key = "audiostarttime", value = focal_stroke.audiotime)
        # update creationtime
        try:
            second_data = update_user_data(second_data, key = "creationtime", value = second_part.data[0].time)
        except:
            second_data = update_user_data(second_data, key = "creationtime")
        second_data["strokes"] = second_part
        # first_data["strokes"] = first_part
        # mimic auto text
        current_cursor.insertText(fake_newline_stroke.to_text().rstrip("\n"))
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_cursor.removeSelectedText()
        current_cursor.insertBlock()
        current_cursor.insertText(second_part.to_text().rstrip("\n"))
        new_block = current_block.next()
        current_block.setUserData(first_data)
        new_block.setUserData(second_data)
        new_block.setUserState(1)
        self.setText("Split: paragraph %d at %d" % (self.block, self.position_in_block))
        log_dict = {"action": "split", "block": self.block, "position_in_block": self.position_in_block}
        log.info(f"Split: {log_dict}")
        self.block_state = current_block.userState()
        current_block.setUserState(1)
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        self.document.setTextCursor(current_cursor)       
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position())
        current_cursor.movePosition(QTextCursor.EndOfBlock)
        current_cursor.deleteChar()
        # removal of the auto text
        for char in self.new_line_stroke.to_text().rstrip("\n"):
            current_cursor.deletePreviousChar()
        # remove the starting space that was removed
        if self.remove_space and self.space_placement == "Before Output":
            current_cursor.insertText(" ")
        restore_data = BlockUserData()
        for key, item in self.block_data.items():
            restore_data = update_user_data(restore_data, key = key, value = item)
        current_block.setUserData(restore_data)
        log_dict = {"action": "merge", "block": self.block}
        log.info(f"Split (undo): {log_dict}")
        self.document.setTextCursor(current_cursor)

class merge_steno_par(QUndoCommand):
    """Merge text and steno from two neighboring textblocks"""
    def __init__(self, cursor, document, block, position_in_block, space_placement, add_space = True):
        super().__init__()
        self.block = block
        self.document = document
        self.position_in_block = position_in_block
        self.space_placement = space_placement
        self.add_space = add_space
        self.first_data_dict = {}
        self.second_data_dict = {} 
        self.block_state = 1   
        self.cursor = cursor    
    def redo(self):
        current_cursor = self.cursor
        first_block_num = self.block
        second_block_num = self.block + 1
        first_block = self.document.document().findBlockByNumber(first_block_num)
        second_block = self.document.document().findBlockByNumber(second_block_num)
        first_data = first_block.userData()
        second_data = second_block.userData()
        self.second_data_dict = deepcopy(second_data.return_all())
        self.first_data_dict = deepcopy(first_data.return_all())
        self.position_in_block = len(first_block.text())
        first_data = update_user_data(first_data, key = "edittime")
        # append second stroke data to first
        second_strokes = second_data["strokes"]
        first_strokes = first_data["strokes"]
        current_cursor.setPosition(first_block.position())
        current_cursor.movePosition(QTextCursor.EndOfBlock)
        if first_data["strokes"].ends_with_element("automatic"):
            for char in first_data["strokes"].data[-1].prefix:
                current_cursor.deletePreviousChar()
        if first_data["strokes"].ends_with("\n"):
            first_data["strokes"].remove_end("\n")
            log.debug("Merge: Removing new line from first paragraph steno")
        if self.space_placement == "Before Output" and self.add_space:
            second_data["strokes"].add_begin(" ")
        elif self.add_space:
            first_data["strokes"].add_end(" ")
        if self.add_space:
            current_cursor.insertText(" ")
        # append the second data to the first
        first_data["strokes"].extend(second_data["strokes"])
        # update the audio end time if it exists, only really needed for last block since other blocks do not have audioendtime
        if first_data["audioendtime"] != second_data["audioendtime"]:
            first_data = update_user_data(first_data, key = "audioendtime", value = second_data["audioendtime"])
        first_block.setUserData(first_data)
        self.block_state = first_block.userState()
        first_block.setUserState(1)
        current_cursor.deleteChar()
        current_cursor.setPosition(first_block.position() + self.position_in_block)
        log_dict = {"action": "merge", "block": self.block}
        log.info(f"Merge: {log_dict}")
        self.document.setTextCursor(current_cursor)
        self.setText("Merge: paragraphs %d & %d" % (first_block_num, second_block_num))
    def undo(self):
        current_cursor = self.document.textCursor()
        first_block_num = self.block
        second_block_num = self.block + 1
        first_block = self.document.document().findBlockByNumber(first_block_num)
        first_data = BlockUserData()
        for key, item in self.first_data_dict.items():
            first_data = update_user_data(first_data, key = key, value = item)
        first_block.setUserData(first_data)
        current_cursor.setPosition(first_block.position())
        if first_data["strokes"].ends_with_element("automatic"):
            current_cursor.setPosition(first_block.position() + self.position_in_block - len(first_data["strokes"].data[-1].prefix))
            current_cursor.insertText(first_data["strokes"].data[-1].prefix)
        else:
            current_cursor.setPosition(first_block.position() + self.position_in_block)
        current_cursor.insertText("\n")
        if self.add_space:
            current_cursor.deleteChar()
        second_block = self.document.document().findBlockByNumber(second_block_num)
        second_data = BlockUserData()
        for key, item in self.second_data_dict.items():
            second_data = update_user_data(second_data, key = key, value = item)
        second_block.setUserData(second_data)
        second_block.setUserState(1)
        log_dict = {"action": "split", "block": self.block, "position_in_block": self.position_in_block}
        log.info(f"Merge (undo): {log_dict}")        
        self.document.setTextCursor(current_cursor)

class set_par_style(QUndoCommand):
    """Set paragraph style"""
    def __init__(self, block, style, document, par_formats, txt_formats):
        super().__init__()
        self.block = block
        self.style = style
        self.document = document
        self.par_formats = par_formats
        self.txt_formats = txt_formats
        self.old_style = ""
        self.block_state = 1
    def redo(self):
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor = self.document.textCursor()
        old_position = current_cursor.position()
        current_cursor.setPosition(current_block.position())
        block_data = current_block.userData()
        if not block_data:
            block_data = BlockUserData()
        if block_data["style"]:
            self.old_style = block_data["style"]
        # if no style specified, fall back to first style available
        if self.style == "":
            self.style = list(self.par_formats.keys())[0]
        block_data = update_user_data(block_data, "style", self.style)
        current_block.setUserData(block_data)
        self.setText(f"Format: set paragraph {self.block} style to {self.style}")
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_cursor.setBlockFormat(self.par_formats[self.style])
        it = current_block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and not frag.charFormat().isImageFormat():
                current_cursor.setPosition(frag.position())
                current_cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                current_cursor.setCharFormat(self.txt_formats[self.style])
            it += 1
        current_cursor.setPosition(old_position)
        self.block_state = current_block.userState()
        current_block.setUserState(1)
        self.document.setTextCursor(current_cursor)
        log_dict = {"action": "set_style", "block": self.block, "style": self.style}
        log.info(f"Style: {log_dict}")
    def undo(self):
        if self.old_style:
            current_block = self.document.document().findBlockByNumber(self.block)
            current_cursor = self.document.textCursor()
            old_position = current_cursor.position()
            current_cursor.setPosition(current_block.position())
            block_data = current_block.userData()
            block_data = update_user_data(block_data, "style", self.old_style)
            current_block.setUserData(block_data)
            current_cursor.movePosition(QTextCursor.StartOfBlock)
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            current_cursor.setBlockFormat(self.par_formats[self.old_style])
            if any([el.element == "image" for el in block_data["strokes"].data]):
                it = current_block.begin()
                while not it.atEnd():
                    frag = it.fragment()
                    if frag.isValid() and not frag.charFormat().isImageFormat():
                        current_cursor.setPosition(frag.position())
                        current_cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                        current_cursor.setCharFormat(self.txt_formats[self.old_style])
                    it += 1
            else:
                current_cursor.setCharFormat(self.txt_formats[self.style])       
            current_cursor.setPosition(old_position)
            self.document.setTextCursor(current_cursor)
            log_dict = {"action": "set_style", "block": self.block, "style": self.old_style}
            log.info(f"Style: {log_dict}")

class style_update(QUndoCommand):
    def __init__(self, styles, style_name, new_style_dict):
        super().__init__()
        self.styles = styles
        self.style_name = style_name
        self.new_style_dict = deepcopy(new_style_dict)
        self.old_style_dict = {}
    def redo(self):
        if self.style_name in self.styles:
            self.old_style_dict = deepcopy(self.styles[self.style_name])
        self.styles[self.style_name] = self.new_style_dict
        log_dict = {"action": "edit_style", "style_dict": self.new_style_dict}
        log.info(f"Style: {log_dict}")
        self.setText(f"Style: update style attributes for style {self.style_name}")
    def undo(self):
        if self.old_style_dict:
            self.styles[self.style_name] = self.old_style_dict
        log_dict = {"action": "edit_style", "style_dict": self.old_style_dict}
        log.info(f"Style undo: {log_dict}")

class update_field(QUndoCommand):
    def __init__(self, cursor, document, block, position, old_dict, new_dict):
        super().__init__()
        self.document = document
        self.block = block
        self.position_in_block = position
        # first is the reference to dict to be updated
        self.user_field_dict = deepcopy(old_dict)
        self.new_dict = deepcopy(new_dict)
        # second one is the copy to be kept for undos
        self.store_dict = deepcopy(old_dict)
        self.cursor = cursor
    def redo(self):
        current_cursor = self.cursor
        current_block = self.document.document().findBlockByNumber(self.block)
        block = self.document.document().begin()
        self.document.set_config_value("user_field_dict", self.new_dict)
        for i in range(self.document.document().blockCount()):     
            block_strokes = block.userData()["strokes"]
            if any([el.element == "field" for el in block_strokes.data]):
                block.setUserState(1)
                for ind, el in enumerate(block_strokes.data):
                    # print(ind)
                    if el.element == "field":
                        start_pos, end_pos = block_strokes.element_pos(ind)
                        # print(block.position() + start_pos)
                        current_cursor.setPosition(block.position() + start_pos)
                        current_cursor.setPosition(block.position() + end_pos, QTextCursor.KeepAnchor)
                        current_cursor.removeSelectedText()
                        el.user_dict = self.new_dict
                        current_cursor.insertText(el.to_text())
            if block == self.document.document().lastBlock():
                break
            block = block.next()
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        self.setText("Fields: update fields")
        log_dict = {"action": "field", "field": self.new_dict}
        log.info(f"Field: {log_dict}")
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        block = self.document.document().begin()
        self.document.set_config_value("user_field_dict", self.store_dict)
        for i in range(self.document.document().blockCount()):   
            block_strokes = block.userData()["strokes"]
            for ind, el in enumerate(block_strokes.data):
                # print(ind)
                if el.element == "field":
                    start_pos, end_pos = block_strokes.element_pos(ind)
                    # print(block.position() + start_pos)
                    current_cursor.setPosition(block.position() + start_pos)
                    current_cursor.setPosition(block.position() + end_pos, QTextCursor.KeepAnchor)
                    current_cursor.removeSelectedText()
                    el.user_dict = self.user_field_dict
                    current_cursor.insertText(el.to_text())
            if block == self.document.document().lastBlock():
                break
            block = block.next()
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        log_dict = {"action": "field", "field": self.store_dict}
        log.info(f"Field: {log_dict}")        

class update_entries(QUndoCommand):
    def __init__(self, cursor, document, block, position, old_dict, new_dict):
        super().__init__()
        self.document = document
        self.block = block
        self.position_in_block = position
        self.new_dict = deepcopy(new_dict)
        # second one is the copy to be kept for undos
        self.store_dict = deepcopy(old_dict)
        self.cursor = cursor
    def redo(self):
        current_cursor = self.cursor
        current_block = self.document.document().findBlockByNumber(self.block)
        block = self.document.document().begin()
        for i in range(self.document.document().blockCount()):    
            block_strokes = block.userData()["strokes"]
            if any([el.element == "index" for el in block_strokes.data]):
                block.setUserState(1)
                for ind, el in enumerate(block_strokes.data):
                    # print(ind)
                    if el.element == "index":
                        start_pos, end_pos = block_strokes.element_pos(ind)
                        current_cursor.setPosition(block.position() + start_pos)
                        current_cursor.setPosition(block.position() + end_pos, QTextCursor.KeepAnchor)
                        current_cursor.removeSelectedText()
                        el.prefix = self.new_dict[el.indexname]["prefix"]
                        el.hidden = self.new_dict[el.indexname]["hidden"]
                        el.description = self.new_dict[el.indexname]["entries"][el.data]
                        current_cursor.insertText(el.to_text())
            if block == self.document.document().lastBlock():
                break
            block = block.next()
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        self.setText("Indices: update indices.")
        log_dict = {"action": "index", "index": self.new_dict}
        log.info(f"Index: {log_dict}")
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        block = self.document.document().begin()
        for i in range(self.document.document().blockCount()):    
            block_strokes = block.userData()["strokes"]
            for ind, el in enumerate(block_strokes.data):
                # print(ind)
                if el.element == "index":
                    start_pos, end_pos = block_strokes.element_pos(ind)
                    current_cursor.setPosition(block.position() + start_pos)
                    current_cursor.setPosition(block.position() + end_pos, QTextCursor.KeepAnchor)
                    current_cursor.removeSelectedText()
                    el.prefix = self.store_dict[el.indexname]["prefix"]
                    el.hidden = self.store_dict[el.indexname]["hidden"]
                    el.description = self.store_dict[el.indexname]["entries"][el.data]
                    current_cursor.insertText(el.to_text())
            if block == self.document.document().lastBlock():
                break
            block = block.next()
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        log_dict = {"action": "index", "index": self.store_dict}
        log.info(f"Index: {log_dict}")  