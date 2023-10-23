import string
import pathlib
import json

from shutil import copyfile
from collections import deque
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository
from dulwich import porcelain

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QCursor, QKeySequence, QTextCursor
from PyQt5.QtCore import QFile, QStringListModel, Qt, QModelIndex, pyqtSignal
from PyQt5.QtWidgets import QPlainTextEdit, QCompleter, QTextEdit, QUndoStack, QMessageBox
from PyQt5.QtMultimedia import (QMediaContent, QMediaPlayer, QMediaRecorder, 
QAudioRecorder, QMultimedia, QVideoEncoderSettings, QAudioEncoderSettings)

_ = lambda txt: QtCore.QCoreApplication.translate("Plover2CAT", txt)

from plover.oslayer.config import CONFIG_DIR
from plover import log

from plover_cat.qcommands import *
from plover_cat.steno_objects import *
from plover_cat.export_helpers import load_odf_styles, recursive_style_format, parprop_to_blockformat, txtprop_to_textformat
from plover_cat.helpers import ms_to_hours, save_json, backup_dictionary_stack, add_custom_dicts, load_dictionary_stack_from_backup
from plover_cat.constants import default_styles, default_config, default_dict

from . __version__ import __version__

class PloverCATEditor(QTextEdit):

    complete = pyqtSignal(QModelIndex)
    send_key = pyqtSignal(str)
    send_del = pyqtSignal()
    send_bks = pyqtSignal()
    send_message = pyqtSignal(str)

    def __init__(self, widget):
        super().__init__(widget)
        # QTextEdit setup
        font = QtGui.QFont()
        font.setFamily("Courier New")
        font.setPointSize(12)
        self.setFont(font)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(False)
        self.setReadOnly(True)
        self.setCursorWidth(5)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard | Qt.TextSelectableByMouse)
        # transcript attributes
        self.engine = None
        self.config = {}
        self.file_name = ""
        self.repo = None
        self.backup_document = {}
        # self.styles_path = ""        
        self.styles = {}
        self.txt_formats = {}
        self.par_formats = {}
        self.user_field_dict = {}
        self.auto_paragraph_affixes = {}    
        self.audio_file = ""
        self.cursor_block = 0
        self.cursor_block_position = 0
        self.stroke_time = ""
        self.last_raw_steno = ""
        self.last_string_sent = ""
        self.last_backspaces_sent = 0
        self.undo_stack = QUndoStack(self)
        self.track_lengths = deque(maxlen = 10)
        self.spell_ignore = []
        self.spellcheck_dicts = []
        self._completer = None
        # media
        self.player = QMediaPlayer()
        self.recorder = QAudioRecorder()
        self.audio_delay = 0
    def setCompleter(self, c):
        if not c:
            self._completer = c
            return
        if self._completer is not None:
            self._completer.activated.disconnect()
        self._completer = c
        c.setWidget(self)
        c.setCompletionMode(QCompleter.PopupCompletion)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.activated[QtCore.QModelIndex].connect(self.insertCompletion)
    def completer(self):
        return self._completer
    def insertCompletion(self, completion):
        if self._completer.widget() is not self:
            return
        self.complete.emit(completion)
    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()
    def showPossibilities(self):
        completionPrefix = self.textUnderCursor()
        if not completionPrefix or not self._completer:
            return
        if completionPrefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(completionPrefix)
            self._completer.popup().setCurrentIndex(
                    self._completer.completionModel().index(0, 0))
        cr = self.cursorRect()
        cr.setWidth(self._completer.popup().sizeHintForColumn(0) + self._completer.popup().verticalScrollBar().sizeHint().width())
        self._completer.complete(cr)
    def focusInEvent(self, e):
        if self._completer is not None:
            self._completer.setWidget(self)
        super(PloverCATEditor, self).focusInEvent(e)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.send_del.emit()
        elif event.key() == Qt.Key_Backspace:
            self.send_bks.emit()
        else:
            if event.key() != Qt.Key_Return:
                if event.modifiers() in [Qt.NoModifier, Qt.ShiftModifier]:
                    self.send_key.emit(event.text())
            QTextEdit.keyPressEvent(self, event)
    def load(self, path, engine):
        self.send_message.emit("Loading data")
        self.file_name = pathlib.Path(path)
        self.file_name.mkdir(parents = True, exist_ok=True)
        self.load_config_file(self.file_name, engine)
        self.load_dicts(engine, self.config["dictionaries"])
        self.load_check_styles(self.config["style"])
        self.load_spellcheck_dicts()
        export_path = self.file_name / "export"
        pathlib.Path(export_path).mkdir(parents = True, exist_ok=True)
        try:
            self.repo = Repo(self.file_name)
            self.dulwich_save()
        except NotGitRepository:
            self.repo = Repo.init(self.file_name)
        self.engine = engine      

    def close_transcript(self):
        if not self.undo_stack.isClean():
            user_choice = QMessageBox.question(self, "Close", "Are you sure you want to close without saving changes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.debug("User choice to close without saving")
                pass
            else:
                log.debug("Abort project close because of unsaved changes.")
                return False
        self.restore_dictionary_from_backup(self.engine)
        if self.recorder.status() == QMediaRecorder.RecordingState:
            self.recorder.stop()
        return True        

    def dulwich_save(self, message = "autosave"):
        transcript_dicts = self.file_name / "dict"
        available_dicts = [transcript_dicts / file for file in transcript_dicts.iterdir()]
        transcript = self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript")
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        files = [transcript, transcript_tape] + available_dicts
        porcelain.add(self.repo.path, paths = files)
        porcelain.commit(self.repo, message = message, author = "plover2CAT <fake_email@fakedomain.com>", committer= "plover2CAT <fake_email@fakedomain.com>")

    def load_config_file(self, path, engine):
        config_path = pathlib.Path(path) / "config.CONFIG"
        if not config_path.exists():
            log.debug("No config file exists. Creating default config file.")
            default_config["space_placement"] = engine.config["space_placement"]
            with open(config_path, "w") as f:
                json.dump(default_config, f)
                log.debug("Project configuration file created.")            
        self.send_message.emit(f"Loading configuration file from {str(config_path)}")
        with open(config_path, "r") as f:
            config_contents = json.loads(f.read())
        log.debug(config_contents)
        self.config = config_contents

    def save_config_file(self):
        config_path = self.file_name / "config.CONFIG"
        log.debug(f"Saving config to {str(config_path)}")
        save_json(self.config, config_path)

    def get_config_value(self, key):
        return(self.config[key])

    def set_config_value(self, key, value):
        self.config[key] = value
        self.save_config_file()

    def load_spellcheck_dicts(self):
        default_spellcheck_path = pathlib.Path(self.file_name) / "spellcheck"
        if default_spellcheck_path.exists():
            self.spellcheck_dicts = [file for file in default_spellcheck_path.iterdir() if str(file).endswith("dic")]

    def load_dicts(self, engine, dictionaries = None):
        list_dicts = engine.config["dictionaries"]
        transcript_dir = self.file_name / "dict"
        transcript_dir.mkdir(parents = True, exist_ok = True)
        default_dict_name = transcript_dir / "default.json"
        has_next = next(transcript_dir.iterdir(), None)
        if not default_dict_name.exists() and not has_next:
            log.debug(f"Creating default dictionary in {str(default_dict_name)}")
            save_json(default_dict, default_dict_name)
            self.config["dictionaries"].append(str(default_dict_name))
        backup_dict_path = self.file_name / "dict" / "dictionaries_backup"
        backup_dictionary_stack(list_dicts, backup_dict_path)
        full_paths = [str(self.file_name / pathlib.Path(i)) for i in self.config["dictionaries"]]
        log.debug("Trying to load dictionaries at %s", full_paths)
        if any(new_dict in list_dicts for new_dict in full_paths):
            log.debug("Checking for duplicate dictionaries with loaded dictionaries.")
            # if any of the new dicts are already in plover
            set_full_paths = set(full_paths)
            set_list_dicts = set(list_dicts)
            full_paths = list(set_full_paths.difference(set_list_dicts))
            dictionaries = [pathlib.Path(i).relative_to(self.file_name) for i in full_paths]
        editor_dict_path = pathlib.Path(CONFIG_DIR) / "plover2cat" / "dict"
        if editor_dict_path.exists():
            available_dicts = [file for file in editor_dict_path.iterdir() if str(file).endswith("json")]
            for dic in available_dicts:
                full_paths.append(str(dic))
        new_dict_config = add_custom_dicts(full_paths, list_dicts)
        engine.config = {'dictionaries': new_dict_config}
        self.config["dictionaries"] = list(set(self.config["dictionaries"] + dictionaries))
        self.save_config_file()

    def restore_dictionary_from_backup(self, engine):
        selected_folder = pathlib.Path(self.file_name)
        log.debug("Attempting to restore dictionaries configuration from backup.")
        backup_dictionary_location = selected_folder / "dict" / "dictionaries_backup"
        log.debug(f"Backup file location: {str(backup_dictionary_location)}")
        if backup_dictionary_location.exists():
            restored_dicts = load_dictionary_stack_from_backup(backup_dictionary_location)
            engine.config = {'dictionaries': restored_dicts}
            log.debug("Dictionaries restored from backup file.")

    def load_check_styles(self, path):
        path = self.file_name / path
        if not path.exists():
            # go to default if the config style doesn't exist
            log.debug("Supplied config style file does not exist. Loading default.")
            path = self.file_name / "styles" / "default.json"
            if not path.exists():
                log.debug("Create default styles for project")
                selected_folder = self.file_name
                style_dir = selected_folder / "styles"
                style_file_name = "default.json"
                style_file_name = style_dir / style_file_name
                save_json(default_styles, style_file_name)
                log.debug(f"Default styles set in {str(style_file_name)}")
        if path.suffix == ".odt":
            log.debug(f"Load odt style file from {str(path)}")
            json_styles = load_odf_styles(path)
        else:
            log.debug(f"Loading JSON style file from {str(path)}")
            # this only checks first level keys, one day, should use the data from this [attribute[1] for attribute in Style(name = "Name").allowed_attributes()],  [attribute[1] for attribute in TextProperties().allowed_attributes()], [attribute[1] for attribute in ParagraphProperties().allowed_attributes()] 
            acceptable_keys = {'styleindex', 'autoupdate', 'class', 'datastylename', 'defaultoutlinelevel', 'displayname', 'family', 'listlevel', 'liststylename', 'masterpagename', 'name', 'nextstylename', 'parentstylename', 'percentagedatastylename', "paragraphproperties", "textproperties"}
            with open(path, "r") as f:
                json_styles = json.loads(f.read())
            for k, v in json_styles.items():
                sub_keys = set([*v])
                # if not sub_keys.issubset(acceptable_keys):
                #     log.warning("Some first-level keys in style json are not valid.")
                #     log.debug(f"First-level keys: {sub_keys}")
                #     self.show_message.emit("Style file failed to parse.")
                #     return False
        log.debug("Styles loaded.")
        original_style_path = path
        new_style_path = self.file_name / "styles" / original_style_path.name
        if original_style_path != new_style_path:
            log.debug(f"Copying style file at {original_style_path} to {new_style_path}")
            copyfile(original_style_path, new_style_path)
            self.config["style"] = new_style_path
        self.styles = json_styles
        self.gen_style_formats()

    def gen_style_formats(self):
        styles_json = self.styles
        txt_formats = {}
        par_formats = {}
        log.debug("Creating block and text formats from styles.")
        for k, v in styles_json.items():
            style_par = recursive_style_format(styles_json, k, prop = "paragraphproperties")
            style_txt = recursive_style_format(styles_json, k, prop = "textproperties")
            par_formats[k] = parprop_to_blockformat(style_par)
            txt_formats[k] = txtprop_to_textformat(style_txt)
        self.txt_formats = txt_formats
        self.par_formats = par_formats        

    def set_style_property(self, name, attribute, value, paragraph = False, text = False):
        if paragraph:
            self.styles[name]["paragraphproperties"][attribute] = value
        elif text:
            self.styles[name]["textproperties"][attribute] = value
        else:
            self.styles[name][attribute] = value

    def get_style_property(self, name, attribute, paragraph = False, text = False):
        if paragraph:
            return(self.styles[name]["paragraphproperties"][attribute])
        elif text:
            return(self.styles[name]["textproperties"][attribute])
        else:
            return(self.styles[name][attribute])
   
    def load_paper_tape(self):
        pass    

    def on_stroke(self, stroke_pressed, end = False):
        current_cursor = self.textCursor()
        current_block = current_cursor.block()        
        stroke_time = datetime.now().isoformat("T", "milliseconds")
        self.update_block_times(current_block, stroke_time)
        string_sent = self.last_string_sent
        backspaces_sent = self.last_backspaces_sent
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()        
        if len(current_block.text()) == 0 and not string_sent and backspaces_sent > 0 and current_block.blockNumber() == 0:
            return
        if string_sent and backspaces_sent > 0 and self.track_lengths[-1] > 0 and backspaces_sent >= self.track_lengths[-1]:
            self.last_raw_steno = self.last_raw_steno + "/" + stroke_pressed.rtfcre
        else:
            self.last_raw_steno = stroke_pressed.rtfcre
        if backspaces_sent != 0:
            cursor_pos = current_cursor.positionInBlock()
            self.track_lengths.append(-1 * backspaces_sent)
            holding_space = backspaces_sent
            current_strokes = current_cursor.block().userData()["strokes"]
            start_pos = backtrack_coord(current_cursor.positionInBlock(), backspaces_sent, 
                        current_strokes.lens(), current_strokes.lengths())
            self.undo_stack.beginMacro(f"Remove: {backspaces_sent} backspaces(s).") 
            if start_pos < 0:
                log.debug(f"{start_pos} backspaces than exists on current paragraph.")
                while start_pos < 0:
                    current_cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
                    self.setTextCursor(current_cursor)
                    self.cut_steno(store=False)
                    holding_space = -1 * start_pos
                    log.debug("%d spaces left" % holding_space)
                    self.merge_paragraphs(add_space = False)
                    # the merge is technically one "backspace"
                    holding_space -= 1
                    current_cursor = self.textCursor()
                    cursor_pos = current_cursor.positionInBlock()
                    current_strokes = current_cursor.block().userData()["strokes"]
                    start_pos = backtrack_coord(current_cursor.positionInBlock(), holding_space, current_strokes.lens(), current_strokes.lengths())
                    log.debug(f"New starting position: {start_pos}.")
                current_cursor.setPosition(current_cursor.block().position() + start_pos, QTextCursor.KeepAnchor)
                self.setTextCursor(current_cursor)
                self.cut_steno(store=False)
            else:
                end_pos = current_cursor.position() - focus_block.position()
                start_pos = backtrack_coord(end_pos, backspaces_sent, focus_block.userData()["strokes"].lens(), focus_block.userData()["strokes"].lengths())
                remove_cmd = steno_remove(current_cursor, self, current_cursor.blockNumber(), start_pos, end_pos - start_pos)
                self.undo_stack.push(remove_cmd)
            self.last_backspaces_sent = 0
            self.undo_stack.endMacro()
            current_cursor = self.textCursor()
            self.cursor_block = current_cursor.blockNumber()
            self.cursor_block_position = current_cursor.positionInBlock()  
        if "\n" in string_sent and string_sent != "\n":
            list_segments = string_sent.splitlines(True)
            self.track_lengths.append(len(self.last_string_sent))
            self.undo_stack.beginMacro(f"Insert: {string_sent}")
            for i, segment in enumerate(list_segments):
                stroke = stroke_text(time = stroke_time, stroke = self.last_raw_steno, text = segment.rstrip("\n"))
                # because this is all occurring in one stroke, only first segment gets the stroke
                if i == 0:
                    self.last_raw_steno = ""
                stroke.audiotime = self.get_audio_time(convert = False)
                if len(stroke) != 0:
                    insert_cmd = steno_insert(current_cursor, self, self.cursor_block, self.cursor_block_position, stroke)
                    self.undo_stack.push(insert_cmd)
                if (i != (len(list_segments) - 1)) or (len(list_segments) == 1) or segment == "\n":
                    self.split_paragraph(remove_space = False)
                current_cursor = self.textCursor()
                # update cursor position for next loop
                self.cursor_block = current_cursor.blockNumber()
                self.cursor_block_position = current_cursor.positionInBlock()
                self.to_next_style()
            self.last_string_sent = ""
            self.undo_stack.endMacro()
            return 
        if string_sent:
            self.track_lengths.append(len(self.last_string_sent))
            stroke = stroke_text(stroke = self.last_raw_steno, text = string_sent)
            stroke.audiotime = self.get_audio_time(convert = False)
            # if self.config["enable_automatic_affix"]:
            #     if self.last_string_sent == "\n":
            #         stroke = self.add_end_auto_affix(stroke, block_dict["style"])
            #     if block_dict["strokes"].element_count() == 0:
            #         stroke = self.add_begin_auto_affix(stroke, block_dict["style"])            
            if not current_cursor.atBlockEnd() and self.last_string_sent == "\n":
                self.split_paragraph()
            else:
                insert_cmd = steno_insert(current_cursor, self, current_block.blockNumber(), current_cursor.positionInBlock(), stroke)
                self.undo_stack.push(insert_cmd)
            self.last_string_sent = ""
        self.document().setModified(True)

    def update_block_times(self, block, edit_time):
        block_dict = block.userData()
        if block_dict:
            block_dict = update_user_data(block_dict, key = "edittime")
        else:
            block_dict = BlockUserData()        
        if not block_dict["creationtime"]:
            block_dict = update_user_data(block_dict, key = "creationtime")
        if not block_dict["audiostarttime"]:
            audio_time = self.get_audio_time()
            if audio_time:
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = audio_time)
        block.setUserData(block_dict)
 
    def merge_paragraphs(self, add_space = True):
        current_document = self
        current_cursor = current_document.textCursor()
        self.cursor_block = current_cursor.blockNumber() - 1
        self.cursor_block_position = current_cursor.positionInBlock()
        merge_cmd = merge_steno_par(current_cursor, self, self.cursor_block, self.cursor_block_position, self.config["space_placement"], add_space = add_space)
        self.undo_stack.push(merge_cmd)

    def split_paragraph(self, remove_space = True):
        current_document = self
        current_cursor = current_document.textCursor()
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
        new_line_stroke = stroke_text(stroke = "R-R", text = "\n")
        # todo
        # if self.config["enable_automatic_affix"]:
        #     new_line_stroke = self.add_end_auto_affix(new_line_stroke, current_cursor.block().userData()["style"])
        split_cmd = split_steno_par(current_cursor, self, self.cursor_block, self.cursor_block_position, self.config["space_placement"], new_line_stroke, remove_space)
        self.undo_stack.push(split_cmd)

    def cut_steno(self, store = True, cut = True):
        action = "Cut" if cut else "Copy"
        current_cursor = self.textCursor()
        if not current_cursor.hasSelection():
            self.send_message.emit("No text selected, select text for {action}")
            return False
        current_block_num = current_cursor.blockNumber()
        current_block = self.document().findBlockByNumber(current_block_num)
        # get coordinates of selection in block
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        stop_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        self.send_message.emit(f"{action}: {action} in paragraph {current_block_num} from {start_pos} to {stop_pos}.")
        selected_text = current_cursor.selectedText()
        if re.search("\u2029", selected_text):
            # maybe one day in the far future
            self.send_message.emit(f"{action} across paragraphs is not supported")
            return False
        block_data = current_block.userData()
        if store:
            self.send_message.emit(f"Extracting from paragraph {current_block_num}, from {start_pos} to {stop_pos}")
            result = block_data["strokes"].extract_steno(start_pos, stop_pos)
            self.send_message.emit("Data stored for pasting")
        if cut:
            self.undo_stack.beginMacro(f"Cut: {selected_text}")
            remove_cmd = steno_remove(current_cursor, self, current_block_num, 
                                start_pos, len(selected_text))
            self.undo_stack.push(remove_cmd)
            self.undo_stack.endMacro()
            log.debug(f"Cut: Cut from paragraph {current_block_num} from {start_pos} to {stop_pos}.")
        if store:
            return(result)

    def navigate_to(self, block_number):
        new_block = self.document().findBlockByNumber(block_number)
        current_cursor = self.textCursor()
        current_cursor.setPosition(new_block.position())
        self.setTextCursor(current_cursor)
        log.debug(f"Editor cursor set to start of block {block_number}.")

    def to_next_style(self):
        # todo
        pass

    def get_audio_time(self, convert = True):
        real_time = None
        if self.player.state() == QMediaPlayer.PlayingState or self.player.state() == QMediaPlayer.PausedState:
            real_time = self.player.position() - self.audio_delay
        elif self.recorder.state() == QMediaRecorder.RecordingState:
            real_time = self.recorder.duration() - self.audio_delay
        if not real_time:
            return("")
        real_time = max(real_time, 0)
        if convert:
            audio_time = ms_to_hours(real_time)
            return(audio_time)
        else:
            return(real_time)
