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
    def __init__(self,  document, block, position_in_block, steno):
        super().__init__()
        self.document = document        
        self.block = block
        self.position_in_block = position_in_block
        self.steno = steno
    def redo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        self.document.setTextCursor(current_cursor)
        if current_block.userData():
            block_data = current_block.userData()
        else:
            block_data = BlockUserData()
        # log.debug("Insert: %s", block_data.return_all())
        log.info("Insert: Insert text at %s" % str(current_block.position() + self.position_in_block))
        # print(block_data.return_all())
        block_data["strokes"].insert_steno(self.position_in_block, self.steno)
        # block_data["strokes"] = new_stroke_data
        block_data = update_user_data(block_data, "edittime")
        # log.debug("Insert: %s", block_data.return_all())
        # current_block.setUserData(block_data)
        current_cursor.insertText(self.steno.to_text())
        self.document.setTextCursor(current_cursor)
        self.setText("Insert: %s" % self.steno.to_text())
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + len(self.steno)
        current_cursor.setPosition(start_pos)
        current_cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        # log.debug("Undo insert: %s", block_data.return_all())
        res = block_data["strokes"].remove_steno(self.position_in_block, self.position_in_block + len(self.steno))
        block_data = update_user_data(block_data, "edittime")
        # current_block.setUserData(block_data)    
        # log.debug("Undo insert: %s", block_data.return_all())
        log.info("Undo insert: Remove %s", current_cursor.selectedText())
        current_cursor.removeSelectedText()
        self.document.setTextCursor(current_cursor)
              
class steno_remove(QUndoCommand):
    """Removes text and steno data from textblock in textdocument"""
    def __init__(self,  document, block, position_in_block, length, steno = ""):
        super().__init__()
        self.document = document
        self.block = block
        self.position_in_block = position_in_block
        self.length = length
        self.steno = steno
    def redo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        # end_pos = current_block.position() + self.position_in_block + self.length
        # log.debug("Remove: start pos: %d, end pos : %d" % (start_pos, end_pos))
        current_cursor.setPosition(start_pos)
        block_data = current_block.userData()
        log.debug("Remove: %d chars" % self.length)
        log.info("Remove: Remove in paragraph %s from %s to %s" % (self.block, self.position_in_block, self.position_in_block + self.length))
        self.steno = block_data["strokes"].remove_steno(self.position_in_block, self.position_in_block + self.length)
        block_data = update_user_data(block_data, "edittime")
        log.debug("Remove: %s", block_data.return_all())
        current_cursor.setPosition(start_pos + len(self.steno), QTextCursor.KeepAnchor)
        self.document.setTextCursor(current_cursor)        
        current_block.setUserData(block_data)
        current_cursor.removeSelectedText()
        self.document.setTextCursor(current_cursor)
        self.setText("Remove: %d chars" % len(self.steno))
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        start_pos = current_block.position() + self.position_in_block
        end_pos = current_block.position() + self.position_in_block + self.length
        # log.debug("Undo remove: start pos: %d, end pos : %d" % (start_pos, end_pos))
        current_cursor.setPosition(start_pos)
        self.document.setTextCursor(current_cursor)
        block_data = current_block.userData()
        # log.debug("Undo remove: %s", block_data.return_all())
        res = block_data["strokes"].insert_steno(self.position_in_block, self.steno)
        log.info("Undo remove: Insert text at %s" % str(current_block.position() + self.position_in_block))
        block_data = update_user_data(block_data, "edittime")
        # log.debug("Undo remove: %s", block_data.return_all())
        current_block.setUserData(block_data)
        current_cursor.insertText(self.steno.to_text())
        self.document.setTextCursor(current_cursor)

class image_insert(QUndoCommand):
    """Insert image into text block"""
    def __init__(self, document, block, position_in_block, image_element):
        super().__init__()
        self.document = document        
        self.block = block
        self.position_in_block = position_in_block
        self.image_element = image_element
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
        # prep image_element
        current_block = self.document.document().findBlockByNumber(self.block)
        current_block.userData()["strokes"].insert_steno(self.position_in_block, self.image_element)
        current_cursor = self.document.textCursor()
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        log.info("Insert: Inserting image %s at position %d" % (self.image_element.path, self.position_in_block))
        current_cursor.insertImage(imageFormat)
        self.setText("Insert image")
        self.document.setTextCursor(current_cursor)
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        current_cursor.setPosition(current_block.position() + self.position_in_block + 1, QTextCursor.KeepAnchor)
        current_block.userData()["strokes"].remove_steno(self.position_in_block, self.position_in_block + 1)
        current_cursor.removeSelectedText()
        self.document.setTextCursor(current_cursor)

class split_steno_par(QUndoCommand):
    """ Splits paragraphs at position in block, and puts steno properly with new textblock """
    def __init__(self, document, block, position_in_block, space_placement):
        super().__init__()
        self.block = block
        self.position_in_block = position_in_block
        self.document = document
        self.strokes = []
        self.space_placement = space_placement
        self.block_text = ""
        self.block_data = ""
    def redo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        current_cursor.setPosition(current_block.position() + self.position_in_block)
        log.info("Split: Splitting at position %d in block %d" % (self.position_in_block, self.block))
        self.block_data = current_block.userData().return_all()
        self.block_text = current_block.text()
        stroke_data = self.block_data["strokes"]
        first_part = stroke_data[0:self.position_in_block]
        second_part = stroke_data[self.position_in_block:]
        first_data = current_block.userData()
        second_data = BlockUserData()
        first_data = update_user_data(first_data, key = "edittime")
        second_data = update_user_data(second_data, key = "edittime")
        # first_text = self.block_text[:self.position_in_block]
        # second_text = self.block_text[self.position_in_block:]
        if second_part and self.space_placement == "Before Output":
            if second_part.starts_with(" "):
                log.debug("Stripping space from beginning of second piece")
                second_part.remove_begin(" ")
        log.debug("Split: Appending new line stroke to end of second piece")
        fake_newline_stroke = stroke_text(stroke = "R-R", text = "\n")
        first_part.append(fake_newline_stroke)
        log.debug("Split: Splitting %s and %s" % (first_part, second_part))
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
        first_data["strokes"] = first_part
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_cursor.removeSelectedText()
        current_cursor.insertBlock()
        current_cursor.insertText(second_part.to_text().rstrip("\n"))
        new_block = current_block.next()
        current_block.setUserData(first_data)
        new_block.setUserData(second_data)
        self.setText("Split: %d,%d" % (self.block, self.position_in_block))
        log.debug("Split: %s", current_cursor.block().userData().return_all())
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        self.document.setTextCursor(current_cursor)       
    def undo(self):
        current_cursor = self.document.textCursor()
        current_block = self.document.document().findBlockByNumber(self.block)
        log.info("Undo split: Merging back at %d, %d" % (self.block, self.position_in_block))
        current_cursor.setPosition(current_block.position())
        current_cursor.setPosition(current_block.position() + self.position_in_block, QTextCursor.KeepAnchor)
        current_cursor.insertText(self.block_data["strokes"].to_text().rstrip("\n"))
        restore_data = BlockUserData()
        for key, item in self.block_data.items():
            restore_data = update_user_data(restore_data, key = key, value = item)
        current_block.setUserData(restore_data)
        next_block = current_block.next()
        current_cursor.setPosition(next_block.position())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()
        log.debug("Undo split: %s", current_cursor.block().userData().return_all())
        self.document.setTextCursor(current_cursor)

class merge_steno_par(QUndoCommand):
    """Merge text and steno from two neighboring textblocks"""
    def __init__(self, document, block, position_in_block, space_placement, add_space = True):
        super().__init__()
        self.block = block
        self.document = document
        self.position_in_block = position_in_block
        self.space_placement = space_placement
        self.add_space = add_space
        self.first_data_dict = {}
        self.second_data_dict = {}        
    def redo(self):
        current_cursor = self.document.textCursor()
        first_block_num = self.block
        second_block_num = self.block + 1
        log.info("Merge: Merging paragraphs %s and %s" % (first_block_num, second_block_num))
        first_block = self.document.document().findBlockByNumber(first_block_num)
        second_block = self.document.document().findBlockByNumber(second_block_num)
        first_data = first_block.userData()
        second_data = second_block.userData()
        self.position_in_block = len(first_block.text())
        first_data = update_user_data(first_data, key = "edittime")
        # append second stroke data to first
        second_strokes = second_data["strokes"]
        first_strokes = first_data["strokes"]
        if first_data["strokes"].ends_with("\n"):
            first_data["strokes"].remove_end("\n")
            log.debug("Merge: Removing new line from first paragraph steno")
        if self.space_placement == "Before Output" and self.add_space:
            second_data["strokes"].add_begin(" ")
        elif self.add_space:
            first_data["strokes"].add_end(" ")
        # append the second data to the first
        first_data["strokes"].extend(second_data["strokes"])
        # update the audio end time if it exists, only really needed for last block since other blocks do not have audioendtime
        if first_data["audioendtime"] != second_data["audioendtime"]:
            first_data = update_user_data(first_data, key = "audioendtime", value = second_data["audioendtime"])
        current_cursor.setPosition(second_block.position())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()
        log.debug("Merge: Deleting second paragraph")
        first_block.setUserData(first_data)
        new_block_text = second_data["strokes"].to_text().rstrip("\n")
        current_cursor.insertText(new_block_text)
        self.second_data_dict = second_data.return_all()
        self.first_data_dict = first_data.return_all()
        current_cursor.setPosition(first_block.position() + self.position_in_block)
        log.debug("Merge: Inserting text %s into paragraph" % new_block_text)
        log.debug("Merge: 2nd paragraph %s" % self.second_data_dict)
        log.debug("Merge: combined paragraph %s" % first_data.return_all())
        self.document.setTextCursor(current_cursor)
        self.setText("Merge: %d & %d" % (first_block_num, second_block_num))
    def undo(self):
        current_cursor = self.document.textCursor()
        first_block_num = self.block
        second_block_num = self.block + 1
        log.info("Undo merge: splitting paragraph %s" % first_block_num)
        first_block = self.document.document().findBlockByNumber(first_block_num)
        current_cursor.setPosition(first_block.position() + self.position_in_block)
        # remove stroke data from cursor pos to end
        self.first_data_dict["strokes"].remove_steno(self.position_in_block, len(self.first_data_dict["strokes"]))
        current_cursor.insertBlock()
        second_block = self.document.document().findBlockByNumber(second_block_num)
        second_data = BlockUserData()
        for key, item in self.second_data_dict.items():
            second_data = update_user_data(second_data, key = key, value = item)
        if self.space_placement == "Before Output" and self.add_space:
            second_data["strokes"].remove_begin(" ")
            current_cursor.setPosition(second_block.position() + 1)
            current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            if current_cursor.selectedText() == " ":
                current_cursor.removeSelectedText()
            current_cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.MoveAnchor)
            # print(second_data["strokes"])
        elif self.add_space:
            self.first_data_dict["strokes"].remove_end(" ")
        fake_newline_stroke = stroke_text(stroke = "R-R", text = "\n")
        self.first_data_dict["strokes"].append(fake_newline_stroke)
        second_block.setUserData(second_data)
        first_data = BlockUserData()
        for key, item in self.first_data_dict.items():
            first_data = update_user_data(first_data, key = key, value = item)
        first_block.setUserData(first_data)        
        # print(second_data.return_all())
        # print(first_block.userData().return_all())
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
        self.old_style = ""
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
        it = current_block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and not frag.charFormat().isImageFormat():
                current_cursor.setPosition(frag.position())
                current_cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                current_cursor.setCharFormat(self.txt_formats[self.style])
            it += 1
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
