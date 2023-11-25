import string
import pathlib
import json
import os
from shutil import copyfile
from collections import deque
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository
from dulwich import porcelain

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QCursor, QKeySequence, QTextCursor, QTextDocument
from PyQt5.QtCore import QFile, QStringListModel, Qt, QModelIndex, pyqtSignal, QUrl
from PyQt5.QtWidgets import QPlainTextEdit, QCompleter, QTextEdit, QUndoStack, QMessageBox, QApplication
from PyQt5.QtMultimedia import (QMediaContent, QMediaPlayer, QMediaRecorder, 
QAudioRecorder, QMultimedia, QVideoEncoderSettings, QAudioEncoderSettings)

_ = lambda txt: QtCore.QCoreApplication.translate("Plover2CAT", txt)

import plover

from plover.oslayer.config import CONFIG_DIR
from plover import log

from plover_cat.qcommands import *
from plover_cat.steno_objects import *
from plover_cat.export_helpers import load_odf_styles, recursive_style_format, parprop_to_blockformat, txtprop_to_textformat
from plover_cat.helpers import ms_to_hours, save_json, backup_dictionary_stack, add_custom_dicts, load_dictionary_stack_from_backup, return_commits, hide_file
from plover_cat.constants import default_styles, default_config, default_dict

from . __version__ import __version__

class PloverCATEditor(QTextEdit):

    complete = pyqtSignal(QModelIndex)
    send_message = pyqtSignal(str)
    send_tape = pyqtSignal(str)
    config_updated = pyqtSignal()
    audio_position_changed = pyqtSignal(int)
    audio_length_changed = pyqtSignal(int)
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
        self.tape = ""
        # self.styles_path = ""        
        self.styles = {}
        self.txt_formats = {}
        self.par_formats = {}
        self.user_field_dict = {}
        self.auto_paragraph_affixes = {}    
        self.numbers = {number: letter for letter, number in plover.system.NUMBERS.items()}
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
        self.audio_file = ""
        self.audio_position = 0
        self.player = QMediaPlayer()
        self.player.durationChanged.connect(self.update_audio_duration)
        self.player.positionChanged.connect(self.update_audio_position)
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
            self.mock_del()
        elif event.key() == Qt.Key_Backspace:
            self.mock_bks()
        else:
            if event.key() != Qt.Key_Return:
                if event.modifiers() in [Qt.NoModifier, Qt.ShiftModifier]:
                    self.mock_type(event.text())
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
        self.load_transcript(self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript"))
        self.load_tape()
        self.engine = engine      

    def load_transcript(self, transcript):
        self.send_message.emit("Transcript file found, loading")
        with open(transcript, "r") as f:
            self.send_message.emit("Reading transcript data.")
            json_document = json.loads(f.read())
        self.backup_document = deepcopy(json_document)
        self.moveCursor(QTextCursor.Start)
        self.clear()
        document_cursor = self.textCursor()
        self.send_message.emit("Loading transcript data.")
        ef = element_factory()
        ea = element_actions()
        self.clear()
        # check if json document is older format
        if "data" in json_document[next(iter(json_document))]:
            # old format json
            for key, value in json_document.items():
                if not key.isdigit():
                    continue
                block_data = BlockUserData()
                el_list = []
                for el in value["data"]["strokes"]:
                    el_dict = {"time": el[0], "stroke": el[1], "data": el[2]}
                    if len(el) == 4:
                        el_dict["audiotime"] = el[4]
                    new_stroke = stroke_text()
                    new_stroke.from_dict(el_dict)
                    el_list.append(new_stroke)
                for k, v in value["data"].items():
                    block_data[k] = v
                block_data["strokes"] = element_collection(el_list)
                document_cursor.setBlockFormat(self.par_formats[block_data["style"]])
                document_cursor.setCharFormat(self.txt_formats[block_data["style"]])                   
                # print(block_data.return_all())
                document_cursor.insertText(value["text"])
                document_cursor.block().setUserData(block_data)
                document_cursor.block().setUserState(1)
                if len(block_data["strokes"]) > 0 and block_data["strokes"].ends_with("\n"):
                    document_cursor.insertText("\n")
                self.send_message.emit(f"Loading paragraph {document_cursor.blockNumber()} of {len(json_document)}")
                QApplication.processEvents()
        else:        
            # new format json  
            for key, value in json_document.items():
                # skip if key is not a digit
                if not key.isdigit():
                    continue
                # document_cursor.insertText(value["text"])
                block_data = BlockUserData()
                el_list = [ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in value["strokes"]]
                # document_cursor.movePosition(QTextCursor.Start)
                self.setTextCursor(document_cursor)
                for k, v in value.items():
                    block_data[k] = v
                block_data["strokes"] = element_collection()
                document_cursor.block().setUserData(block_data)
                block_data["strokes"] = element_collection(el_list)
                if block_data["style"] not in self.par_formats:
                    block_data["style"] = next(iter(self.par_formats))
                document_cursor.setBlockFormat(self.par_formats[block_data["style"]])
                document_cursor.setCharFormat(self.txt_formats[block_data["style"]])                
                if any([el.element == "image" for el in el_list]):
                    for el in el_list:
                        if el.element == "image":
                            imageUri = QUrl("file://{0}".format(el.path))
                            image = QImage(QImageReader(el.path).read())
                            self.document().addResource(
                                QTextDocument.ImageResource,
                                imageUri,
                                QVariant(image)
                            )
                            imageFormat = QTextImageFormat()
                            imageFormat.setWidth(image.width())
                            imageFormat.setHeight(image.height())
                            imageFormat.setName(imageUri.toString())
                            document_cursor.insertImage(imageFormat)
                            document_cursor.setCharFormat(self.txt_formats[block_data["style"]])                
                        else:
                            document_cursor.insertText(el.to_text())
                else:
                    document_cursor.insertText(block_data["strokes"].to_text())
                self.send_message.emit(f"Loading paragraph {document_cursor.blockNumber()} of {len(json_document)}")
                QApplication.processEvents()
        if document_cursor.block().userData() == None:
            document_cursor.block().setUserData(BlockUserData())
        self.undo_stack.clear()
        self.send_message.emit("Loaded transcript.")   

    def load_tape(self):
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        if pathlib.Path(transcript_tape).is_file():
            self.send_message.emit("Tape file found, loading.")
            self.tape = transcript_tape.read_text()
            self.send_message.emit("Loaded tape.")

    def save(self, path = None):
        # todo: use path in future to save everywhere
        selected_folder = pathlib.Path(self.file_name)
        self.save_config_file()
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")        
        self.save_transcript(transcript)
        if str(self.config["style"]).endswith(".json"):
            save_json(self.styles, self.styles_path)
        self.document().setModified(False)
        self.undo_stack.setClean()
        self.dulwich_save(message = "user save")
        self.send_message.emit("Saved project data")  

    def save_as(self, path):
        # todo
        # use pathlib to explore everything, replace stem, 
        # disable for now, deal with paths for image assets in json
        self.send_message.emit("Temporarily disabled.")

    def save_transcript(self, path):      
        json_document = self.backup_document
        self.send_message.emit("Extracting block data for transcript save")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.send_message.emit("Saving transcript data.")
        block = self.document().begin()
        status = 0
        for i in range(self.document().blockCount()):
            if block.userState() == 1:
                status = 1
            if status == 1:
                if block.userData():
                    block_dict = deepcopy(block.userData().return_all())
                else:
                    return False
                block_num = block.blockNumber()
                block_dict["strokes"] = block_dict["strokes"].to_json()
                json_document[str(block_num)] = block_dict
                block.setUserState(-1)
            if block == self.document().lastBlock():
                break
            block = block.next()      
        self.send_message.emit(f"Saving transcript data to {str(path)}")
        if len(json_document) > self.document().blockCount():
            for num in range(self.document().blockCount(), len(json_document)):
                self.send_message.emit(f"Extra paragraphs in backup document. Removing {num}.")
                json_document.pop(str(num), None)
        save_json(json_document, path)
        QApplication.restoreOverrideCursor()
        return True

    def autosave(self):
        if self.undo_stack.isClean():
            return
        transcript_dir = pathlib.Path(self.file_name)
        transcript_name = "." + str(transcript_dir.stem) + ".transcript"
        transcript = transcript_dir / transcript_name
        self.send_message.emit(f"Autosaving to {transcript}.")
        transcript = pathlib.Path(transcript)
        if transcript.exists():
            transcript.unlink()
        save_res = self.save_transcript(transcript)       
        if save_res and os.name == "nt":
            # hide file on windows systems
            hide_file(str(transcript))
            self.send_message.emit("Autosave complete.")
         
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

    def get_dulwich_commits(self):
        commit_choices = return_commits(self.repo)
        return(commit_choices)

    def revert_transcript(self, commit_id):
        transcript = str(self.file_name.stem) + (".transcript")
        porcelain.reset_file(self.repo, transcript, commit_id)
        new_commit_message = "revert to %s" % commit_id.decode("ascii")
        self.dulwich_save(message=new_commit_message)
        self.undo_stack.clear()
        self.clear()
        transcript = self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript")
        if pathlib.Path(transcript).is_file():
            self.load_transcript(transcript)
        self.setCursorWidth(5)
        self.moveCursor(QTextCursor.End)

    def load_config_file(self, path, engine = None):
        config_path = pathlib.Path(path) / "config.CONFIG"
        if not config_path.exists():
            log.debug("No config file exists. Creating default config file.")
            if not engine and not self.engine:
                default_config["space_placement"] = "Before Output"
            elif engine:
                default_config["space_placement"] = engine.config["space_placement"]
            else:
                default_config["space_placement"] = self.engine.config["space_placement"]
            with open(config_path, "w") as f:
                json.dump(default_config, f)
                log.debug("Project configuration file created.")            
        self.send_message.emit(f"Loading configuration file from {str(config_path)}")
        with open(config_path, "r") as f:
            config_contents = json.loads(f.read())
        log.debug(config_contents)
        self.config = config_contents
        self.user_field_dict = self.config["user_field_dict"]
        self.auto_paragraph_affixes = self.config["auto_paragraph_affixes"]

    def save_config_file(self):
        config_path = self.file_name / "config.CONFIG"
        log.debug(f"Saving config to {str(config_path)}")
        save_json(self.config, config_path)

    def get_config_value(self, key):
        return(self.config[key])

    def set_config_value(self, key, value):
        self.config[key] = value
        self.save_config_file()
        self.load_config_file(self.file_name)
        self.config_updated.emit()

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
   
    def on_stroke(self, stroke_pressed, end = False):
        current_cursor = self.textCursor()
        current_block = current_cursor.block()        
        stroke_time = datetime.now().isoformat("T", "milliseconds")
        self.update_block_times(current_block, stroke_time)
        string_sent = self.last_string_sent
        backspaces_sent = self.last_backspaces_sent
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()        
        self.stroke_time = stroke_time
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
                end_pos = current_cursor.position() - current_block.position()
                start_pos = backtrack_coord(end_pos, backspaces_sent, current_block.userData()["strokes"].lens(), current_block.userData()["strokes"].lengths())
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
            if self.config["enable_automatic_affix"]:
                if self.last_string_sent == "\n":
                    stroke = self.add_end_auto_affix(stroke, current_block.userData()["style"])
                if current_block.userData()["strokes"].element_count() == 0:
                    stroke = self.add_begin_auto_affix(stroke, current_block.userData()["style"])            
            if not current_cursor.atBlockEnd() and self.last_string_sent == "\n":
                self.split_paragraph()
            else:
                insert_cmd = steno_insert(current_cursor, self, current_block.blockNumber(), current_cursor.positionInBlock(), stroke)
                self.undo_stack.push(insert_cmd)
            self.last_string_sent = ""
        self.document().setModified(True)

    def log_to_tape(self, stroke):
        keys = set()
        for key in stroke.steno_keys:
            if key in self.numbers:
                keys.add(self.numbers[key])
                keys.add(plover.system.NUMBER_KEY)
            else:
                keys.add(key)
        steno = ''.join(key.strip('-') if key in keys else ' ' for key in plover.system.KEYS)
        audio_time = self.get_audio_time()
        log_string = "{0}|{1}|({2},{3})\t|{4}|".format(self.stroke_time, audio_time, self.cursor_block, self.cursor_block_position, steno)
        self.send_tape.emit(log_string)
        self.tape = "\n".join([self.tape, log_string])
        # self.tape.append(log_string + "\n")
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        with open(transcript_tape, "a") as f:
            f.write(log_string)
            f.write("\n")

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
        if self.config["enable_automatic_affix"]:
            new_line_stroke = self.add_end_auto_affix(new_line_stroke, current_cursor.block().userData()["style"])
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

    def mock_del(self): 
        current_cursor = self.textCursor()
        if current_cursor.hasSelection():
            self.cut_steno(store = False)
        else:
            if current_cursor.atBlockEnd():
                return
            else:
                block_strokes = current_cursor.block().userData()["strokes"]
                # "delete" means removing one ahead, so has to "reverse" to get start pos
                start_pos = backtrack_coord(current_cursor.positionInBlock() + 1, 1, block_strokes.lens(), block_strokes.lengths())
                current_cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
                current_cursor.setPosition(current_cursor.block().position() + start_pos, QTextCursor.KeepAnchor)
                self.setTextCursor(current_cursor)
                self.cut_steno(store = False)  

    def insert_text(self, text = None):
        current_cursor = self.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = current_cursor.block()
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        self.undo_stack.beginMacro(f"Insert: {text}")
        fake_steno = text_element(text = text)
        insert_cmd = steno_insert(current_cursor, self, current_block_num, start_pos, fake_steno)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()   

    def insert_field(self, name):
        el = text_field(name = name, user_dict = self.user_field_dict)
        current_cursor = self.textCursor()
        current_block = current_cursor.blockNumber()
        start_pos = current_cursor.positionInBlock()
        insert_cmd = steno_insert(current_cursor, self, current_block, start_pos, el)
        self.undo_stack.push(insert_cmd)

    def update_fields(self, new_field_dict):
        current_cursor = self.textCursor()
        update_cmd = update_field(current_cursor, self, current_cursor.blockNumber(), current_cursor.positionInBlock(), self.user_field_dict, new_field_dict)
        self.undo_stack.push(update_cmd)
        # self.update_field_menu()   

    def extract_indexes(self):
        index_dict = {}
        current_cursor = self.textCursor()
        block = self.document().begin()
        # if len(self.toPlainText()) == 0:
        #     return(index_dict)
        for i in range(self.document().blockCount()):
            # print(block.blockNumber())
            if block.userData():
                block_strokes = block.userData()["strokes"]
                for ind, el in enumerate(block_strokes.data):
                    # print(ind)
                    if el.element == "index":
                        if el.indexname not in index_dict:
                            index_dict[el.indexname] = {}
                        if "prefix" not in index_dict[el.indexname]:
                            index_dict[el.indexname]["prefix"] = el.prefix
                        if "hidden" not in index_dict[el.indexname]:
                            index_dict[el.indexname]["hidden"] = el.hidden
                        if "entries" not in index_dict[el.indexname]:
                            index_dict[el.indexname]["entries"] = {}
                        index_dict[el.indexname]["entries"][el.data] = el.description
            if block == self.document().lastBlock():
                break
            block = block.next()
        return(index_dict)       

    def insert_index_entry(self, el):
        current_cursor = self.textCursor()
        start_pos = current_cursor.positionInBlock()
        current_block = current_cursor.blockNumber()
        self.undo_stack.beginMacro("Insert: index entry")
        if current_cursor.hasSelection() and el == None:
            self.cut_steno(store = False)
            self.setTextCursor(current_cursor)
            start_pos = current_cursor.positionInBlock()
        else:
            current_cursor.setPosition(min(current_cursor.position(), current_cursor.anchor()))
            start_pos = current_cursor.positionInBlock()
        insert_cmd = steno_insert(current_cursor, self, current_block, start_pos, el)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()
        self.send_message.emit("Index inserted.")

    def update_indices(self, old, new):
        current_cursor = self.textCursor()
        current_block = current_cursor.blockNumber()
        start_pos = current_cursor.positionInBlock()            
        update_cmd = update_entries(current_cursor, self, current_block, start_pos, old, new)
        self.undo_stack.push(update_cmd)

    def add_begin_auto_affix(self, element, style):
        if style not in self.auto_paragraph_affixes:
            return(element)
        auto_el = automatic_text(prefix = self.auto_paragraph_affixes[style]["prefix"])  
        auto_el.from_dict(element.to_json())
        auto_el.element = "automatic"
        return(auto_el)                    

    def add_end_auto_affix(self, element, style):
        if style not in self.auto_paragraph_affixes:
            return(element)
        auto_el = automatic_text(prefix = self.auto_paragraph_affixes[style]["suffix"])  
        auto_el.from_dict(element.to_json())
        auto_el.element = "automatic"
        return(auto_el)    

    def mock_type(self, text):
        if self.engine.output:
            return          
        if len(text) > 0:
            self.insert_text(text)        

    def mock_bks(self):
        if self.engine.output:
            return      
        current_cursor = self.textCursor()
        if current_cursor.atBlockStart():
            return
        current_cursor.movePosition(QTextCursor.PreviousCharacter)
        self.setTextCursor(current_cursor)
        self.mock_del()

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
    
    def load_audio(self, path):
        self.audio_file = pathlib.Path(path)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(self.audio_file))))
        self.send_message.emit(f"Player set to selected audio {str(path)}.")

    def play_pause_audio(self):
        if self.recorder.state() == QMediaRecorder.StoppedState:
            pass
        else:
            self.send_message.emit("Recording in progress.")
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.send_message.emit("Paused audio")
        else:
            self.player.play()
            self.send_message.emit("Playing audio")
    
    def update_audio_duration(self, duration):
        self.audio_length_changed.emit(duration)
    
    def update_audio_position(self, position):
        self.audio_position = position
        self.audio_position_changed.emit(position)
