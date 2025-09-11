import string
import pathlib
import json
import os
from shutil import copyfile, copytree
from collections import deque
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository
from dulwich import porcelain
from spylls.hunspell import Dictionary

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QCursor, QKeySequence, QTextCursor, QTextDocument, QColor, QUndoStack
from PySide6.QtCore import QFile, QStringListModel, Qt, QModelIndex, Signal, QUrl, QSettings
from PySide6.QtWidgets import QCompleter, QTextEdit,  QMessageBox, QApplication
from PySide6.QtMultimedia import (QMediaPlayer, QMediaRecorder, QMediaDevices, QMediaCaptureSession, QMediaFormat, QAudioOutput)

_ = lambda txt: QtCore.QCoreApplication.translate("Plover2CAT", txt)

import plover

from plover.oslayer.config import CONFIG_DIR
from plover import log

from plover_cat.qcommands import *
from plover_cat.steno_objects import *
from plover_cat.rtf_parsing import *
from plover_cat.export_helpers import load_odf_styles, recursive_style_format, parprop_to_blockformat, txtprop_to_textformat
from plover_cat.helpers import ms_to_hours, save_json, backup_dictionary_stack, add_custom_dicts, load_dictionary_stack_from_backup, return_commits, hide_file
from plover_cat.constants import default_styles, default_config, default_dict

class PloverCATEditor(QTextEdit):
    """Editor object for a transcript.

    The editor is separated from the window, containing all transcript data,
    and settings that are unique to each transcript. No changes to the GUI,
    except those to the `QTextEdit` itself should be made here.

    :ivar new_open: ``True`` if transcript in temporary directory
    :ivar engine: Plover existing engine instance
    :ivar dict config: transcript configuration
    :ivar file_name: transcript directory path
    :ivar repo: ``dulwich`` repository instance
    :ivar dict backup_document: original transcript data, ``paragraph number: block data``
    :ivar str tape: transcript tape contents as a long string with new line separators
    :ivar dict styles: transcript style parameters
    :ivar dict txt_formats: ``QTextCharFormat`` objects for each style by name
    :ivar dict par_formats: ``QTextBlockFormat`` objects for each style by name
    :ivar dict highlight_colors: ``QColor`` objects for each element type
    :ivar dict user_field_dict: dict ref of ``self.config["user_field_dict"]``
    :ivar dict auto_paragraph_affixes: dict ref of ``self.config["auto_paragraph_affixes"]``
    :ivar int cursor_block: block that current cursor was in on last stroke
    :ivar int cursor_block_position: position in ``cursor_block`` of current cursor on last stroke
    :ivar str stroke_time: time of last stroke
    :ivar str last_raw_steno: last stroke 
    :ivar str last_string_sent: string sent by Plover on last stroke
    :ivar int last_backspaces_sent: number of backspaces sent by Plover on last stroke
    :ivar list track_lengths: ``deque`` of length 10 that tracks length of ``last_string_sent`` and ``last_backspaces_sent``
    :ivar undo_stack: ``QUndoStack``
    :ivar list spell_ignore: words to ignore in spellcheck, session only
    :ivar dictionary: ``spylls`` dictionary 
    :ivar dictionary_name: name of ``dictionary``, usually the language code
    :ivar audio_file: path to file being played/recorded
    :ivar player: ``QMediaPlayer``
    :ivar media_recorder: ``QMediaCaptureSession`` that manages audio input for recording
    :ivar recorder: ``QMediaCaptureSession`` attached to ``media_recorder``
    :ivar int audio_position: current position of media being played
    :ivar int audio_delay: offset to subtract from ``audio_position``

    """
    send_message = Signal(str)
    """Signal to send with message to display."""
    send_tape = Signal(str)
    """Signal to send with tape contents."""
    audio_position_changed = Signal(int)
    """Signal to send with new audio position."""
    audio_length_changed = Signal(int)
    """Signal to send with new audio duration."""
    def __init__(self, widget):
        super().__init__(widget)
        # QTextEdit setup
        self.setUndoRedoEnabled(False)
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
        self.new_open = False
        self.engine = None
        self.config = {}
        self.file_name = ""
        self.repo = None
        self.backup_document = {}
        self.tape = ""       
        self.styles = {}
        self.txt_formats = {}
        self.par_formats = {}
        self.highlight_colors = {}
        self.user_field_dict = {}
        self.auto_paragraph_affixes = {}    
        self.numbers = {number: letter for letter, number in plover.system.NUMBERS.items()}
        self.cursor_block = 0
        self.cursor_block_position = 0
        self.stroke_time = ""
        self.last_raw_steno = ""
        self.last_string_sent = ""
        self.last_backspaces_sent = 0
        self.track_lengths = deque(maxlen = 10)
        self.undo_stack = QUndoStack(self)
        self.spell_ignore = []
        self.dictionary = Dictionary.from_files('en_US')
        self.dictionary_name = "en_US"
        self._completer = None
        # media
        self.audio_file = ""
        self.player = QMediaPlayer()
        output = QAudioOutput(self.player)
        self.player.setAudioOutput(output)
        self.player.durationChanged.connect(self.update_audio_duration)
        self.player.positionChanged.connect(self.update_audio_position)
        self.media_recorder = QMediaCaptureSession()
        self.recorder = QMediaRecorder()
        self.media_recorder.setRecorder(self.recorder)
        self.recorder.errorOccurred.connect(self.recorder_error)
        self.recorder.recorderStateChanged.connect(log.debug)
        self.audio_position = 0
        self.audio_delay = 0

    def setCompleter(self, c):
        """Set autocompletion for transcript."""
        if not c:
            self._completer = c
            return
        if self._completer is not None:
            self._completer.activated.disconnect()
        self._completer = c
        c.setWidget(self)
        c.setCompletionMode(QCompleter.PopupCompletion)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.activated[QtCore.QModelIndex].connect(self.insert_autocomplete)

    def completer(self):
        """Return completer."""
        return self._completer

    def textUnderCursor(self):
        """Return work under cursor."""
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def showPossibilities(self):
        """Show autocompletion possibilities."""
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
        """Set completer when in focus."""
        # autocomplete code mostly from https://stackoverflow.com/questions/60451045/
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
            # print(event.key())
            QTextEdit.keyPressEvent(self, event)
    def recorder_error(self, error, message):
        log.debug(f"{error}: {message}")

    def load(self, path, engine, load_transcript = True):
        """Load transcript and associated data.

        The associated ``load_*`` methods will create necessary files if none exist.
        
        :param path: path of transcript to load
        :param engine: Plover engine instance
        :param bool load_transcript: load transcript data, default ``True``
        """
        self.send_message.emit("Loading data")
        self.file_name = pathlib.Path(path)
        self.file_name.mkdir(parents = True, exist_ok = True)
        self.load_config_file(self.file_name, engine)
        self.load_dicts(engine, self.config["dictionaries"])
        self.load_check_styles(self.file_name / self.config["style"])
        self.get_highlight_colors()
        self.load_spellcheck_dict()
        export_path = self.file_name / "export"
        pathlib.Path(export_path).mkdir(parents = True, exist_ok = True)
        try:
            self.repo = Repo(self.file_name)
            self.dulwich_save()
        except NotGitRepository:
            self.repo = Repo.init(self.file_name)
            self.dulwich_save()
        transcript = self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript")
        if load_transcript and transcript.is_file():
            self.load_transcript(transcript)
        self.load_tape()
        self.engine = engine      

    def load_transcript(self, transcript):
        """Load transcript steno data.

        :param transcript: path to transcript file
        """
        self.send_message.emit("Transcript file found, loading")
        with open(transcript, "r") as f:
            self.send_message.emit("Reading transcript data.")
            json_document = json.loads(f.read())
        self.backup_document = deepcopy(json_document)
        self.send_message.emit("Loading transcript data.")
        # check if json document is older format
        if not json_document:
            return
        if "data" in json_document[next(iter(json_document))]:
            self.backup_document = import_version_one(json_document)
        else:
            self.backup_document = import_version_two(json_document)
        self.clear()
        self.moveCursor(QTextCursor.Start)
        document_cursor = self.textCursor()
        ef = element_factory()
        for key, value in self.backup_document.items():
            # skip if key is not a digit
            if not key.isdigit():
                continue
            block_data = BlockUserData()
            el_list = [ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in value["strokes"]]
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
            for el in el_list:
                if el.element == "image":
                    i_path = self.file_name / pathlib.Path(el.path)
                    imageUri = QUrl(i_path.as_uri())
                    el.path = i_path.as_posix()
                    image = QImage(QImageReader(el.path).read())
                    self.document().addResource(
                        QTextDocument.ImageResource,
                        imageUri,
                        image
                    )
                    imageFormat = QTextImageFormat()
                    imageFormat.setWidth(image.width())
                    imageFormat.setHeight(image.height())
                    imageFormat.setName(imageUri.toString())
                    document_cursor.insertImage(imageFormat)
                    document_cursor.setCharFormat(self.txt_formats[block_data["style"]])                
                else:
                    current_format = self.txt_formats[block_data["style"]]
                    current_format.setForeground(self.highlight_colors[el.element])            
                    document_cursor.insertText(el.to_text(), current_format)
            self.send_message.emit(f"Loading paragraph {document_cursor.blockNumber()} of {len(json_document)}")
            QApplication.processEvents()
        if document_cursor.block().userData() == None:
            document_cursor.block().setUserData(BlockUserData())
            self.to_next_style()
        self.undo_stack.clear()
        self.send_message.emit("Loaded transcript.")   

    def load_tape(self):
        """Load tape data."""
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        if pathlib.Path(transcript_tape).is_file():
            self.send_message.emit("Tape file found, loading.")
            self.tape = transcript_tape.read_text()
            self.send_message.emit("Loaded tape.")

    def save(self):
        """Save transcript."""
        selected_folder = pathlib.Path(self.file_name)
        self.save_config_file()
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")        
        self.save_transcript(transcript)
        if str(self.config["style"]).endswith(".json"):
            self.save_style_file()
        self.undo_stack.setClean()
        self.dulwich_save(message = "user save")
        self.send_message.emit("Saved project data")  

    def save_as(self, new_path):
        """Save transcript to new location.

        :param new_path: directory path
        """
        transcript_dir = pathlib.Path(new_path)
        transcript_dir.mkdir()
        self.save_config_file(transcript_dir/ "config.CONFIG")
        transcript_name = transcript_dir.joinpath(transcript_dir.stem).with_suffix(".transcript")        
        self.save_transcript(transcript_name)
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        if transcript_tape.exists():
            new_tape = transcript_dir.joinpath(transcript_dir.stem).with_suffix(".tape")
            copyfile(transcript_tape, new_tape)
        transcript_style = self.file_name / self.config["style"]
        transcript_dir.joinpath("styles").mkdir()
        new_style = transcript_dir / self.config["style"]
        copyfile(transcript_style, new_style)
        if self.file_name.joinpath("assets").exists():
            asset_dir = transcript_dir / "assets"
            copytree(self.file_name.joinpath("assets"), asset_dir)
        if self.file_name.joinpath("dict").exists():
            dict_dir = transcript_dir / "dict"
            copytree(self.file_name.joinpath("dict"), dict_dir)
        if self.file_name.joinpath("audio").exists():
            audio_dir = transcript_dir / "audio"
            copytree(self.file_name.joinpath("audio"), audio_dir)            

    def save_transcript(self, path): 
        """Extract transcript steno data and save.

        :param path: transcript file path
        """     
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
                    continue
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
        if not json_document:
            json_document = {}
        save_json(json_document, path)
        QApplication.restoreOverrideCursor()
        return True

    def autosave(self):
        """Save transcript data to backup file."""
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
        """Clean up transcript for close."""
        if not self.undo_stack.isClean():
            user_choice = QMessageBox.question(self, "Plover2CAT", "Are you sure you want to close without saving changes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.debug("User choice to close without saving")
                pass
            else:
                log.debug("Abort project close because of unsaved changes.")
                return False
        self.restore_dictionary_from_backup(self.engine)
        if self.recorder.recorderState() == QMediaRecorder.RecordingState:
            self.recorder.stop()
        return True        

    def clear_transcript(self):
        """Clears all transcript data.
        """
        self.clear()
        self.backup_document = {}

    def dulwich_save(self, message = "autosave"):
        """Commit transcript files to ``dulwich`` repo.

        :param str message: commit message
        """
        transcript_dicts = self.file_name / "dict"
        available_dicts = [transcript_dicts / file for file in transcript_dicts.iterdir()]
        transcript = self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript")
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        files = [transcript, transcript_tape] + available_dicts
        porcelain.add(self.repo.path, paths = files)
        porcelain.commit(self.repo, message = message, author = "plover2CAT <fake_email@fakedomain.com>", committer= "plover2CAT <fake_email@fakedomain.com>")

    def get_dulwich_commits(self):
        """Get most recent commits from ``dulwich`` repo."""
        commit_choices = return_commits(self.repo)
        return(commit_choices)

    def revert_transcript(self, commit_id):
        """Revert transcript to previous commit based on commit id.
        """
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
        """Load transcript configuration."""
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
        new_vals = {"page_line_numbering": False, "page_linenumbering_increment": 1, "page_timestamp": False, "page_max_char": 0, "page_max_line": 0, 
                    "header_left": "", "header_center": "", "header_right": "", 
                    "footer_left": "", "footer_center": "", "footer_right": "", "enable_automatic_affix": False,
                    "user_field_dict": user_field_dict, "auto_paragraph_affixes": {}}
        new_vals.update(config_contents)
        self.config = new_vals
        self.user_field_dict = self.config["user_field_dict"]
        self.auto_paragraph_affixes = self.config["auto_paragraph_affixes"]

    def save_config_file(self, config_path = None):
        """Save configuration file.

        :param config_path: path to save configuration
        """
        if not config_path:
            config_path = self.file_name / "config.CONFIG"
        log.debug(f"Saving config to {str(config_path)}")
        save_json(self.config, config_path)

    def get_config_value(self, key):
        """Get configuration value by key."""
        return(self.config[key])

    def set_config_value(self, key, value):
        """Set configuration value by key."""
        cmd = update_config_value(key, value, self.config)
        self.undo_stack.push(cmd)

    def load_spellcheck_dict(self, dic_path = "en_US"):
        """Load spellchecking dictionary for ``spylls``.
        
        :param str dic_path: language code or path to dic files
        """
        self.dictionary = Dictionary.from_files(dic_path)
        self.dictionary_name = pathlib.Path(dic_path).stem

    def load_dicts(self, engine, dictionaries = None):
        """Load dictionaries for transcript.

        Note that loading dictionaries is not an undo-able action at this point.

        :param list dictionaries: paths to dictionary files
        """
        list_dicts = engine.config["dictionaries"]
        transcript_dir = self.file_name / "dict"
        transcript_dir.mkdir(parents = True, exist_ok = True)
        default_dict_name = transcript_dir / "default.json"
        has_next = next(transcript_dir.iterdir(), None)
        if not default_dict_name.exists() and not has_next:
            log.debug(f"Creating default dictionary in {str(default_dict_name)}")
            save_json(default_dict, default_dict_name)
            dictionaries.append(str(pathlib.Path("dict/default.json")))
        backup_dict_path = self.file_name / "dict" / "dictionaries_backup"
        backup_dictionary_stack(list_dicts, backup_dict_path)
        full_paths = [str(self.file_name / pathlib.Path(i)) for i in dictionaries]
        log.debug("Trying to load dictionaries at %s", full_paths)
        if any(new_dict in list_dicts for new_dict in full_paths):
            log.debug("Checking for duplicate dictionaries with loaded dictionaries.")
            # if any of the new dicts are already in plover
            set_full_paths = set(full_paths)
            set_list_dicts = set(list_dicts)
            full_paths = list(set_full_paths.difference(set_list_dicts))
            dictionaries = [pathlib.Path(i).relative_to(self.file_name) for i in full_paths]
        # add dicts that should load for all transcripts
        editor_dict_path = pathlib.Path(CONFIG_DIR) / "plover2cat" / "dict"
        if editor_dict_path.exists():
            available_dicts = [file for file in editor_dict_path.iterdir() if str(file).endswith("json")]
            for dic in available_dicts:
                full_paths.append(str(dic))
        new_dict_config = add_custom_dicts(full_paths, list_dicts)
        engine.config = {'dictionaries': new_dict_config}
        self.config["dictionaries"] = list(set(self.config["dictionaries"] + dictionaries))

    def add_dict(self, dictionary):
        """
        Add dictionary to transcript.

        :param dictionary: path string for dictionary to add
        """

        dictionary_path = pathlib.Path(dictionary)
        new_dict_path = self.file_name / "dict" / dictionary_path.name
        if new_dict_path != dictionary_path:
            log.debug(f"Copying dictionary at {str(dictionary_path)} to {str(new_dict_path)}")
            copyfile(dictionary_path, new_dict_path)
        transcript_dicts = self.get_config_value("dictionaries")
        engine_dicts = self.engine.config["dictionaries"]
        if str(dictionary_path) in engine_dicts:
            self.send_message.emit("Selected dictionary is already in loaded dictionaries, passing.")
            return
        new_dict_config = add_custom_dicts([str(new_dict_path)], engine_dicts) 
        self.engine.config = {'dictionaries': new_dict_config} 
        # relative_to will be removed version 3.14, change once plover drops support for before 3.10
        # can use new_dict_path.parents[-1] / new_dict_path.name
        transcript_dicts.append(str(new_dict_path.relative_to(self.file_name)))  

    def remove_dict(self, dictionary):
        dictionary_path = pathlib.Path(dictionary)
        dictionary_list = self.get_config_value("dictionaries")
        list_dicts = self.engine.config["dictionaries"]
        list_dicts = [i.path for i in list_dicts if pathlib.Path(i.path) != dictionary_path]
        new_dict_config = add_custom_dicts(list_dicts, [])
        self.engine.config = {'dictionaries': new_dict_config}
        if str(dictionary_path.relative_to(self.file_name)) in dictionary_list:
            dictionary_list = [i for i in dictionary_list if i != str(dictionary_path.relative_to(self.file_name))]
            self.send_message.emit(f"Remove {str(dictionary_path.relative_to(self.file_name))} from config")
            self.config["dictionaries"] = dictionary_list
        else:
            self.send_message.emit("Selected dictionary not a transcript dictionary, passing.")

    def restore_dictionary_from_backup(self, engine):
        """Restore dictionaries from backup file.

        :param engine: Plover engine instance
        """
        selected_folder = pathlib.Path(self.file_name)
        log.debug("Attempting to restore dictionaries configuration from backup.")
        backup_dictionary_location = selected_folder / "dict" / "dictionaries_backup"
        log.debug(f"Backup file location: {str(backup_dictionary_location)}")
        if backup_dictionary_location.exists():
            restored_dicts = load_dictionary_stack_from_backup(backup_dictionary_location)
            engine.config = {'dictionaries': restored_dicts}
            log.debug("Dictionaries restored from backup file.")

    def get_highlight_colors(self):
        """Obtain element highlight colors from saved settings.
        """
        self.highlight_colors = {}
        settings = QSettings("Plover2CAT-4", "OpenCAT")
        el_names = ["stroke", "text", "automatic", "field", "index"]
        for el in el_names:
            key = f"color{el.title()}"
            if settings.contains(key):
                el_color = settings.value(key)
            else:
                el_color = "black"
            self.highlight_colors[el] = QColor(el_color)

    def load_check_styles(self, path):
        """Load a style JSON or ODF file.

        :param path: path to style file.
        """
        # path = self.file_name / path
        path = pathlib.Path(path)
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
        posix_path = pathlib.Path("styles").joinpath(original_style_path.name).as_posix()
        self.config["style"] = posix_path
        self.styles = json_styles
        self.gen_style_formats()

    def gen_style_formats(self):
        """Generate ``QText*Format`` objects from style dictionary.
        """
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
        """Set a style attribute given name, and type of property.

        :param str name: name of style
        :param str attribute: attribute to set
        :param str value: new value for attribute
        :param bool paragraph: set attribute in "paragraphproperties"
        :param bool text: set attribute in "textproperties"
        """
        if paragraph:
            self.styles[name]["paragraphproperties"][attribute] = value
        elif text:
            self.styles[name]["textproperties"][attribute] = value
        else:
            self.styles[name][attribute] = value

    def set_style_properties(self, name, properties):
        """Set all attributes for a style.

        :param str name: name of style
        :param dict properties: style attributes
        """
        cmd = update_style(self, self.styles, name, properties)
        self.undo_stack.push(cmd)

    def get_style_property(self, name, attribute, paragraph = False, text = False):
        """Get style attribute.
        :param str name: style name
        :param str attribute: style attribute
        :param bool paragraph: obtain attribute from paragraphproperties
        :param bool text: obtain attribute from textproperties 
        """
        styles_json = self.styles
        for k, v in styles_json.items():
            style_par = recursive_style_format(styles_json, k, prop = "paragraphproperties")
            style_txt = recursive_style_format(styles_json, k, prop = "textproperties")        
        if paragraph:
            return(style_par[name][attribute])
        elif text:
            return(style_txt[name][attribute])
        else:
            return(self.styles[name][attribute])

    def set_paragraph_style(self, style, block = None):
        """Set style of paragraph in transcript.

        :param str style: name of style
        :param int block: paragraph block number
        """
        if not block:
            block = self.textCursor().blockNumber()
        if self.textCursor().hasSelection():
            current_cursor = self.textCursor()
            start_pos = current_cursor.selectionStart()
            end_pos = current_cursor.selectionEnd()
            current_cursor.setPosition(start_pos)
            begin_block = current_cursor.blockNumber()
            current_cursor.setPosition(end_pos)
            end_block = current_cursor.blockNumber()
            self.undo_stack.beginMacro(f"Styling paragraphs {begin_block}-{end_block}.")
            for block in range(begin_block, end_block):
                style_cmd = set_par_style(self.textCursor(), self, block, style, self.par_formats, self.txt_formats)
                self.undo_stack.push(style_cmd)
            self.undo_stack.endMacro()
        else:
            style_cmd = set_par_style(self.textCursor(), self, block, style, self.par_formats, self.txt_formats)
            self.undo_stack.push(style_cmd)

    def set_paragraph_property(self, paragraph, prop, value):
        """Set a paragraph's property.

        :param int paragraph: paragraph block number
        :param str prop: property name
        :param value: value
        """
        prop_cmd = set_par_property(self, paragraph, prop, value)
        self.undo_stack.push(prop_cmd)

    def refresh_par_style(self, block = None):
        """Update a paragraph's display styling.

        :param block:  ``QTextBlock`` instance
        """
        if not block:
            block = self.textCursor().block()
        block_data = block.userData()["strokes"]
        block_style = block.userData()["style"]
        current_cursor = self.textCursor()          
        current_cursor.setPosition(block.position())
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        current_cursor.setBlockFormat(self.par_formats[block_style])
        current_cursor.movePosition(QTextCursor.StartOfBlock)
        for el in block_data:
            current_cursor.setPosition(current_cursor.position() + len(el), QTextCursor.KeepAnchor)
            temp_format = self.txt_formats[block_style]
            if el.element != "image":
                temp_format.setForeground(self.highlight_colors[el.element])
                current_cursor.setCharFormat(temp_format)
                current_cursor.clearSelection()

    def save_style_file(self):
        """Save current styles to style file."""
        style_file_path = self.file_name / self.config["style"]
        log.debug(f"Saving styles to {str(style_file_path)}")
        save_json(self.styles, style_file_path)

    def to_next_style(self):
        """Set current paragraph style based on previous style.
        #todo change to using block number rather than taking cursor
        """
        current_cursor = self.textCursor()
        current_block = current_cursor.block()
        if current_cursor.blockNumber() == 0:
            return
        style_data = self.styles
        if len(style_data) == 0:
            return
        # keep using style as default if nothing is set
        previous_style = None
        new_style = current_cursor.block().userData()["style"]
        previous_block = current_block.previous()
        if previous_block:
            previous_dict = previous_block.userData()
            previous_style = previous_dict["style"]
        if previous_style and "nextstylename" in style_data[previous_style]:
            new_style = style_data[previous_style]["nextstylename"]
        self.set_paragraph_style(new_style)
        
    def on_stroke(self, stroke_pressed, end = False):
        """Write.

        :param stroke_pressed: stroke sent to Plover
        :param bool end: always append writing to end of transcript
        """
        current_cursor = self.textCursor()
        if end:
            current_cursor.movePosition(QTextCursor.End)
            self.setTextCursor(current_cursor)
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

    def log_to_tape(self, stroke):
        """Log stroke to transcript tape.

        :param stroke: stroke to log
        """
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
        """Update paragraph timestamps.

        :param block: reference to a ``QTextBlock``
        :param edit_time: 
        """
        block_dict = block.userData()
        if not block_dict:
            block_dict = BlockUserData() 
        block_dict = update_user_data(block_dict, "edittime", edit_time)     
        if not block_dict["creationtime"]:
            block_dict = update_user_data(block_dict, key = "creationtime")
        if not block_dict["audiostarttime"]:
            audio_time = self.get_audio_time()
            if audio_time:
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = audio_time)
        block.setUserData(block_dict)
 
    def merge_paragraphs(self, add_space = True):
        """Merge two paragraphs.

        :param bool add_space: add space between paragraph when merging
        """
        current_document = self
        current_cursor = current_document.textCursor()
        if current_cursor.blockNumber() == 0:
            return
        current_cursor.movePosition(QTextCursor.PreviousBlock)
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
        self.setTextCursor(current_cursor)
        merge_cmd = merge_steno_par(current_cursor, self, self.cursor_block, self.cursor_block_position, self.config["space_placement"], add_space = add_space)
        self.undo_stack.push(merge_cmd)

    def split_paragraph(self, remove_space = True):
        """Split one paragraph into two.

        :param bool remove_space: remove space from beginning of new second paragraph if exist
        """
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
        """Remove selected text and steno.

        :param bool store: store removed data
        :param bool cut: whether cut or paste action, for message display
        """
        action = "Cut" if cut else "Copy"
        current_cursor = self.textCursor()
        if not current_cursor.hasSelection():
            self.send_message.emit("No text selected, select text for {action}")
            return False
        current_block_num = current_cursor.blockNumber()
        current_block = self.document().findBlockByNumber(current_block_num)
        # get coordinates of selection in block
        start_pos = current_cursor.selectionStart() - current_block.position()
        stop_pos = current_cursor.selectionEnd() - current_block.position()
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

    def replace(self, steno = "", replace_term = None):
        """Replace selected text with stroke element.

        :param str steno: stroke for stroke element
        :param str replace_term: text for stroke element, the replacement text
        """
        log.debug("Replace %s with %s", self.textCursor().selectedText(), replace_term)
        self.undo_stack.beginMacro(f"Replace: {self.textCursor().selectedText()} with {replace_term}")
        current_cursor = self.textCursor()
        current_block = current_cursor.block()
        start_pos = current_cursor.selectionStart() - current_block.position()
        fake_steno = stroke_text(stroke = steno, text = replace_term)
        remove_cmd = steno_remove(current_cursor, self, current_cursor.blockNumber(), start_pos, 
                        len(self.textCursor().selectedText()))
        self.undo_stack.push(remove_cmd)    
        insert_cmd = steno_insert(current_cursor, self, current_cursor.blockNumber(), start_pos, fake_steno)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()        

    def mock_del(self): 
        """Delete selection or one character after cursor.
        """
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
        """Insert text element at cursor.

        :param str text: text for text element.
        """
        current_cursor = self.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = current_cursor.block()
        start_pos = current_cursor.selectionStart() - current_block.position()
        self.undo_stack.beginMacro(f"Insert: {text}")
        fake_steno = text_element(text = text)
        insert_cmd = steno_insert(current_cursor, self, current_block_num, start_pos, fake_steno)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()   

    def insert_field(self, name):
        """Insert field at cursor.
        """
        el = text_field(name = name, user_dict = self.user_field_dict)
        current_cursor = self.textCursor()
        current_block = current_cursor.blockNumber()
        start_pos = current_cursor.positionInBlock()
        insert_cmd = steno_insert(current_cursor, self, current_block, start_pos, el)
        self.undo_stack.push(insert_cmd)

    def insert_image(self, img_path):
        """Insert image at cursor.

        :param img_path: path to image
        """
        selected_file = pathlib.Path(img_path)
        im_element = image_text(path = selected_file.as_posix())
        insert_cmd = image_insert(self.textCursor(), self, self.textCursor().blockNumber(), 
                        self.textCursor().positionInBlock(), im_element)
        self.undo_stack.push(insert_cmd)

    def update_fields(self, new_field_dict):
        """Update existing field elements with new values.

        :param dict new_field_dict: updated field dict
        """
        current_cursor = self.textCursor()
        update_cmd = update_field(current_cursor, self, current_cursor.blockNumber(), current_cursor.positionInBlock(), self.user_field_dict, new_field_dict)
        self.undo_stack.push(update_cmd) 

    def extract_indexes(self):
        """Extract existing index entries from transcript.

        :return: dictionary of indices with nested entries
        """
        index_dict = {}
        current_cursor = self.textCursor()
        block = self.document().begin()
        # if len(self.toPlainText()) == 0:
        #     return(index_dict)
        for i in range(self.document().blockCount()):
            # print(block.blockNumber())
            if block.userData():
                block_strokes = block.userData()["strokes"]
                for ind, el in enumerate(block_strokes):
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
        """Insert index entry at cursor.

        :param el: index entry element
        """
        current_cursor = self.textCursor()
        start_pos = current_cursor.positionInBlock()
        current_block = current_cursor.blockNumber()
        self.undo_stack.beginMacro("Insert: index entry")
        if current_cursor.hasSelection() and el == None:
            self.cut_steno(store = False)
            self.setTextCursor(current_cursor)
            start_pos = current_cursor.positionInBlock()
        else:
            current_cursor.setPosition(current_cursor.selectionStart())
            start_pos = current_cursor.positionInBlock()
        insert_cmd = steno_insert(current_cursor, self, current_block, start_pos, el)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()
        self.send_message.emit("Index inserted.")

    def update_indices(self, old, new):
        """Update all index entries.

        :param dict old: existing indices data
        :param dict new: new indices data
        """
        current_cursor = self.textCursor()
        current_block = current_cursor.blockNumber()
        start_pos = current_cursor.positionInBlock()            
        update_cmd = update_entries(current_cursor, self, current_block, start_pos, old, new)
        self.undo_stack.push(update_cmd)

    def add_begin_auto_affix(self, element, style):
        """Add paragraph prefix based on style.

        :param element: element to add affix to
        :param style: style for paragraph element is from
        :return: new element, now ``automatic``
        """
        if style not in self.auto_paragraph_affixes:
            return(element)
        auto_el = automatic_text(prefix = self.auto_paragraph_affixes[style]["prefix"])  
        auto_el.from_dict(element.to_json())
        auto_el.element = "automatic"
        return(auto_el)                    

    def add_end_auto_affix(self, element, style):
        """Add paragraph suffix based on style.

        :param element: element to add affix to
        :param style: style for paragraph element is from
        :return: new element, now ``automatic``
        """
        if style not in self.auto_paragraph_affixes:
            return(element)
        auto_el = automatic_text(prefix = self.auto_paragraph_affixes[style]["suffix"])  
        auto_el.from_dict(element.to_json())
        auto_el.element = "automatic"
        return(auto_el)    

    def insert_autocomplete(self, index):
        """Insert selected autocomplete candidate.

        :param int index: index of selection from pop-up widget
        """
        if self._completer.widget() is not self:
            return
        steno = index.data(QtCore.Qt.UserRole)
        text = index.data()
        current_cursor = self.textCursor()
        current_block = current_cursor.block()
        current_cursor.select(QTextCursor.WordUnderCursor)
        start_pos = current_cursor.selectionStart() - current_block.position()
        end_pos = current_cursor.selectionEnd() - current_block.position()
        self.send_message.emit(f"Autocomplete: autocomplete word {text} from {start_pos} to {end_pos}.")
        start_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(start_pos)
        end_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(end_pos)
        current_cursor.setPosition(current_block.position() + start_stroke_pos[0])
        current_cursor.setPosition(current_block.position() + end_stroke_pos[1], QTextCursor.KeepAnchor)
        self.setTextCursor(current_cursor)
        selected_text = current_cursor.selectedText()
        if self.config["space_placement"] == "Before Output" and selected_text.startswith(" "):
            text = " " + text
        else:
            # this is unlikely as after output would not trigger autocomplete 
            text = text + " "
        autocomplete_steno = stroke_text(stroke = steno, text = text)
        self.undo_stack.beginMacro("Autocomplete: %s" % text)
        remove_cmd = steno_remove(current_cursor, self, current_cursor.blockNumber(), 
                        current_cursor.anchor() - current_block.position(), len(selected_text))
        self.undo_stack.push(remove_cmd)
        current_cursor = self.textCursor()
        insert_cmd = steno_insert(current_cursor, self, current_cursor.blockNumber(), 
                        current_cursor.positionInBlock(), autocomplete_steno)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()

    def mock_type(self, text):
        """Mock typing from keyboard.

        :param str text: text to insert
        """
        if self.engine.output:
            return          
        if len(text) > 0:
            self.insert_text(text)        

    def mock_bks(self):
        """Mock one backspace.
        """
        if self.engine.output:
            return      
        current_cursor = self.textCursor()
        if current_cursor.atBlockStart():
            return
        current_cursor.movePosition(QTextCursor.PreviousCharacter)
        self.setTextCursor(current_cursor)
        self.mock_del()

    def navigate_to(self, block_number):
        """Move cursor to beginning of a block by number.

        :param int block_number: paragraph number to move to
        """
        new_block = self.document().findBlockByNumber(block_number)
        current_cursor = self.textCursor()
        current_cursor.setPosition(new_block.position())
        self.setTextCursor(current_cursor)
        log.debug(f"Editor cursor set to start of block {block_number}.")

    def get_audio_time(self, convert = True):
        """Get audio time from media.

        :param bool convert: convert to str timestamp
        :return: timestamp if ``convert = True``, or milliseconds if ``False``
        """
        real_time = None
        if self.player.playbackState() == QMediaPlayer.PlayingState or self.player.playbackState() == QMediaPlayer.PausedState:
            real_time = self.player.position() - self.audio_delay
        elif self.recorder.recorderState() == QMediaRecorder.RecordingState:
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
        """Load media file.

        :param str path: path to media file
        """
        self.audio_file = pathlib.Path(path)
        self.player.setSource(QUrl.fromLocalFile(str(self.audio_file)))
        self.send_message.emit(f"Player set to selected audio {str(path)}.")

    def play_pause_audio(self):
        """Play or pause media.
        """
        if self.recorder.recorderState() == QMediaRecorder.StoppedState:
            pass
        else:
            self.send_message.emit("Recording in progress.")
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.send_message.emit("Paused audio")
        else:
            self.player.play()
            self.send_message.emit("Playing audio")
    
    def update_audio_duration(self, duration):
        """Send new duration to GUI.
        
        :param int duration: media duration
        """
        self.audio_length_changed.emit(duration)
    
    def update_audio_position(self, position):
        """Send new position in media.

        :param int position: media position
        """
        self.audio_position = position
        self.audio_position_changed.emit(position)
