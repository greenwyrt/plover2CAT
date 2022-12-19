import collections
import time
from plover import log
from PyQt5.QtGui import QTextBlockUserData, QTextDocument, QTextCursor, QTextBlock
from PyQt5.QtWidgets import QUndoCommand
from datetime import datetime, timezone
from plover_cat.stroke_funcs import *

class BlockUserData(QTextBlockUserData):
    """Representation of the data for a block, from ninja-ide"""
    def __init__(self):
        QTextBlockUserData.__init__(self)
        self.attrs = collections.defaultdict(str)
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
    if not value:
        value = datetime.now().isoformat("T", "milliseconds")
    new_dict[key] = value
    return new_dict 

class steno_insert(QUndoCommand):
    """Inserts text and steno data into textblock in textdocument"""
    block = None
    position_in_block = None
    text = None
    length = None
    steno = []
    document = None
    def __init__(self, block, position_in_block, text, length, steno, document):
        super().__init__()
        self.block = block
        self.position_in_block = position_in_block
        self.text = text
        self.length = length
        if len(steno) > 0:
            if not all(isinstance(el, list) for el in steno):
                steno = [steno]
        self.steno = steno
        self.document = document
    def redo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        # log.debug("Insert: %s", block_data.return_all())
        before, after = split_stroke_data(block_data["strokes"], self.position_in_block)
        log.debug("Insert: Splitting pieces %s and %s with %s" % (before, after, self.steno))
        if before and after:
            before = before + self.steno
            before = before + after
            new_stroke_data = before
        elif before and not after:
            new_stroke_data = before + self.steno
        elif not before and after:
            new_stroke_data = self.steno + after
        else:
            new_stroke_data = self.steno
        # if before:
        #     new_stroke_data = before + self.steno
        # else:
        #     new_stroke_data = self.steno
        # if not self.text.endswith("\n") and after:
        #     new_stroke_data = new_stroke_data + after
        # else:
        #     continue
        log.info("Insert: Insert text at %s" % str(current_block.position() + self.position_in_block))
        block_data["strokes"] = new_stroke_data
        block_data = update_user_data(block_data, "edittime")
        # log.debug("Insert: %s", block_data.return_all())
        current_block.setUserData(block_data)
        current_cursor.insertText(self.text)
        self.document.setTextCursor(current_cursor)
        self.setText("Insert: %s" % self.text)
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + self.length
        current_cursor.setPosition(start_pos)
        current_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        # log.debug("Undo insert: %s", block_data.return_all())
        remainder, cut_steno = extract_stroke_data(block_data["strokes"], self.position_in_block, self.position_in_block + self.length, copy = False)
        block_data["strokes"] = remainder
        block_data = update_user_data(block_data, "edittime")
        current_block.setUserData(block_data)    
        # log.debug("Undo insert: %s", block_data.return_all())
        log.info("Undo insert: Remove %s", current_cursor.selectedText())
        current_cursor.removeSelectedText()
        self.document.setTextCursor(current_cursor)
              
class steno_remove(QUndoCommand):
    """Removes text and steno data from textblock in textdocument"""
    block = None
    position_in_block = None
    text = None
    length = None
    steno = []
    document = None
    def __init__(self, block, position_in_block, text, length, steno, document):
        super().__init__()
        self.block = block
        self.position_in_block = position_in_block
        self.text = text
        self.length = length
        if len(steno) > 0:
            if not all(isinstance(el, list) for el in steno):
                steno = [steno]
        self.steno = steno
        self.document = document
    def redo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + self.length
        log.debug("Remove: start pos: %d, end pos : %d" % (start_pos, end_pos))
        current_cursor.setPosition(start_pos)
        current_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        log.debug("Remove: %d chars" % self.length)
        log.info("Remove: Remove in paragraph %s from %s to %s" % (self.block, self.position_in_block, self.position_in_block + self.length))
        remainder, cut_steno = extract_stroke_data(block_data["strokes"], self.position_in_block, self.position_in_block + self.length, copy = False)
        block_data["strokes"] = remainder
        # block_data = update_user_data(block_data, key = "strokes", value = remainder)
        block_data = update_user_data(block_data, "edittime")
        # log.debug("Remove: %s", block_data.return_all())
        current_block.setUserData(block_data)
        self.steno = cut_steno  
        current_cursor.removeSelectedText()
        self.document.setTextCursor(current_cursor)
        self.setText("Remove: %d chars" % self.length)
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + self.length
        log.debug("Undo remove: start pos: %d, end pos : %d" % (start_pos, end_pos))
        current_cursor.setPosition(start_pos)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        # log.debug("Undo remove: %s", block_data.return_all())
        before, after = split_stroke_data(block_data["strokes"], self.position_in_block)
        log.debug("Undo remove: Splitting pieces %s and %s with %s" % (before, after, self.steno))
        if before and after:
            before = before + self.steno
            before = before + after
            new_stroke_data = before
        elif before and not after:
            new_stroke_data = before + self.steno
        elif not before and after:
            new_stroke_data = self.steno + after
        else:
            new_stroke_data = self.steno
        log.info("Undo remove: Insert text at %s" % str(current_block.position() + self.position_in_block))
        block_data["strokes"] = new_stroke_data
        block_data = update_user_data(block_data, "edittime")
        # log.debug("Undo remove: %s", block_data.return_all())
        current_block.setUserData(block_data)
        current_cursor.insertText(self.text)
        self.document.setTextCursor(current_cursor)

class split_steno_par(QUndoCommand):
    """ Splits paragraphs at position in block, and puts steno properly with new textblock """
    block = None
    position_in_block = None
    document = None
    strokes = []
    space_placement = ""
    block_text = ""
    def __init__(self, block, position_in_block, space_placement, document):
        super().__init__()
        self.block = block
        self.position_in_block = position_in_block
        self.document = document
        self.space_placement = space_placement
    def redo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        log.info("Split: Splitting at position %d in block %d" % (self.position_in_block, self.block))
        self.block_data = current_block.userData()
        self.block_text = current_block.text()
        stroke_data = self.block_data["strokes"]
        first_part, second_part = split_stroke_data(stroke_data, self.position_in_block)
        first_text = self.block_text[:self.position_in_block]
        second_text = self.block_text[self.position_in_block:]
        if second_part and self.space_placement == "Before Output":
            if second_part[0][2].startswith(" "):
                log.debug("Stripping space from beginning of second piece")
                second_part[0][2] = second_part[0][2].lstrip(" ")
                second_text = second_text.lstrip(" ")
        log.debug("Split: Appending new line stroke to end of second piece")
        fake_newline_stroke = [datetime.now().isoformat("T", "milliseconds"), "R-R", "\n"]
        first_part.append(fake_newline_stroke)
        first_data = current_block.userData()
        second_data = BlockUserData()
        self.strokes = stroke_data
        log.debug("Split: Splitting %s and %s" % (first_part, second_part))
        second_data["strokes"] = second_part
        # this is important on last segment that has audioendtime
        if first_data["audioendtime"]:
            second_data = update_user_data(second_data, key = "audioendtime", value = first_data["audioendtime"])
            first_data = update_user_data(first_data, key = "audioendtime", value = "")
        # check the strokes if there is an audio time associated with stroke
        # use first stroke that has an audio time
        focal_stroke = next((stroke for stroke in second_part if len(stroke) > 3), None)
        if focal_stroke:
            second_data = update_user_data(second_data, key = "audiostarttime", value = focal_stroke[3])
        # update creationtime
        try:
            second_data = update_user_data(second_data, key = "creationtime", value = second_part[0][0])
        except:
            second_data = update_user_data(second_data, key = "creationtime")
        second_data = update_user_data(second_data, key = "edittime")
        first_data["strokes"] = first_part
        first_data = update_user_data(first_data, key = "edittime")
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_cursor.removeSelectedText()
        current_cursor.insertBlock()
        current_cursor.insertText(second_text)
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        self.document.setTextCursor(current_cursor)
        new_block = current_block.next()
        current_block.setUserData(first_data)
        new_block.setUserData(second_data)
        self.setText("Split: %d,%d" % (self.block, self.position_in_block))
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        second_text = self.block_text[self.position_in_block:]
        log.info("Undo split: Merging back at %d, %d" % (self.block, self.position_in_block))
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        if self.space_placement == "Before Output":
            if not second_text.startswith(" "):
                second_text = " " + second_text
        current_cursor.insertText(second_text)
        block_data = current_block.userData()
        block_data["strokes"] = self.strokes
        current_block.setUserData(block_data)
        next_block = current_block.next()
        current_cursor.setPosition(next_block.position())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()
        self.document.setTextCursor(current_cursor)

class merge_steno_par(QUndoCommand):
    """Merge text and steno from two neighboring textblocks"""
    block = None
    position_in_block = None
    text = None
    first_data_dict = {}
    second_data_dict = {}
    space_placement = ""
    first_block_text = ""
    second_block_text = ""
    add_space = True
    def __init__(self, block, position_in_block, space_placement, document, add_space = True):
        super().__init__()
        self.block = block
        self.space_placement = space_placement
        self.document = document
        self.add_space = add_space
    def redo(self):
        current_cursor = self.document.textCursor()
        first_block_num = self.block
        second_block_num = self.block + 1
        log.info("Merge: Merging paragraphs %s and %s" % (first_block_num, second_block_num))
        first_block = self.document.document().findBlockByNumber(first_block_num)
        second_block = self.document.document().findBlockByNumber(second_block_num)
        self.position_in_block = len(first_block.text())
        first_block_text = first_block.text()
        second_block_text = second_block.text()
        first_data = first_block.userData()
        second_data = second_block.userData()
        self.first_data_dict = first_data.return_all()
        self.second_data_dict = second_data.return_all()
        first_data = update_user_data(first_data, key = "edittime")
        # append second stroke data to first
        second_strokes = second_data["strokes"]
        first_strokes = first_data["strokes"]
        if first_strokes[-1][2] == "\n":
            log.debug("Merge: Removing new line from first paragraph steno")
            del first_strokes[-1]
        elif first_strokes[-1][2].endswith("\n"):
            log.debug("Merge: Removing new line from first paragraph steno")
            first_strokes[-1][2] = first_strokes[-1][2].rstrip()
        if self.space_placement == "Before Output" and self.add_space:
            second_strokes[0][2] = " " + second_strokes[0][2]
        elif self.add_space:
            first_strokes[-1][2] = first_strokes[-1][2] + " "
        if self.add_space:
            new_block_text = " " + second_block.text()
        else:
            new_block_text = second_block.text()
        self.second_block_text = new_block_text
        new_strokes = first_strokes + second_strokes
        first_data["strokes"] = new_strokes
        # update the audio end time if it exists, only really needed for last block since other blocks do not have audioendtime
        if first_data["audioendtime"] != second_data["audioendtime"]:
            first_data = update_user_data(first_data, key = "audioendtime", value = second_data["audioendtime"])
        current_cursor.setPosition(second_block.position())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()
        log.debug("Merge: Deleting second paragraph")
        first_block.setUserData(first_data)
        current_cursor.insertText(new_block_text)
        current_cursor.setPosition(first_block.position() + self.position_in_block)
        log.debug("Merge: Inserting text %s into paragraph" % new_block_text)
        self.document.setTextCursor(current_cursor)
        self.setText("Merge: %d & %d" % (first_block_num, second_block_num))
    def undo(self):
        current_cursor = self.document.textCursor()
        first_block_num = self.block
        second_block_num = self.block + 1
        log.info("Undo merge: splitting paragraph %s" % first_block_num)
        first_block = self.document.document().findBlockByNumber(first_block_num)
        first_data = first_block.userData()
        fake_newline_stroke = [datetime.now().isoformat("T", "milliseconds"), "R-R", "\n"]
        first_strokes = self.first_data_dict["strokes"]
        first_strokes.append(fake_newline_stroke)            
        first_data["strokes"] = first_strokes
        first_block.setUserData(first_data)
        current_cursor.setPosition(first_block.position() + self.position_in_block)
        # if self.add_space:
        #     current_cursor.setPosition(first_block.position() + self.position_in_block - 1)
        current_cursor.insertBlock()
        second_block = self.document.document().findBlockByNumber(second_block_num)
        second_data = second_block.userData()
        if self.space_placement == "Before Output" and self.add_space:
            self.second_data_dict["strokes"][0][2] = self.second_data_dict["strokes"][0][2].lstrip(" ")
            current_cursor.setPosition(second_block.position() + 1)
            current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            current_cursor.removeSelectedText()
        for key, item in self.second_data_dict.items():
            second_data = update_user_data(second_data, key = key, value = item)
        second_block.setUserData(second_data)
        self.document.setTextCursor(current_cursor)

class set_par_style(QUndoCommand):
    """Set paragraph style"""
    block = None
    old_style = ""
    style = ""
    def __init__(self, block, style, document, par_formats, txt_formats):
        super().__init__()
        self.block = block
        self.style = style
        self.document = document
        self.par_formats = par_formats
        self.txt_formats = txt_formats
    def redo(self):
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor = self.document.textCursor()
        old_position = current_cursor.position()
        current_cursor.setPosition(current_block.position())
        # current_cursor.setCharFormat(self.txt_formats[self.style])
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
        self.setText("Style: Par. %d set style %s" % (self.block, self.style))
        log.info("Style: Par. %d set style %s" % (self.block, self.style))
        log.debug("Style: New style is %s, old style is %s" % (self.style, self.old_style))
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_cursor.setBlockFormat(self.par_formats[self.style])
        current_cursor.setCharFormat(self.txt_formats[self.style])
        current_cursor.setPosition(old_position)
        self.document.setTextCursor(current_cursor)
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
            current_cursor.setCharFormat(self.txt_formats[self.old_style])
            log.info("Undoing styling: %s to par %d." % (self.style, self.block))
            log.debug("Undoing styling: from new style %s to old style %s" % (self.style, self.old_style))
            current_cursor.setPosition(old_position)
            self.document.setTextCursor(current_cursor)
