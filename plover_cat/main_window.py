import os
import subprocess
import string
import re
import pathlib
import json
import textwrap
import html
import collections

from datetime import datetime, timezone
from collections import Counter, deque
from shutil import copyfile
from copy import deepcopy
from sys import platform

from odf.opendocument import OpenDocumentText, load
from odf.office import FontFaceDecls
from odf.style import Style, TextProperties, ParagraphProperties, FontFace, PageLayout, PageLayoutProperties, MasterPage, TabStops, TabStop
from odf.text import H, P, Span, Tab, LinenumberingConfiguration
from odf.teletype import addTextToElement

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QBrush, QColor, QTextCursor, QTextBlockUserData, QFont, QTextDocument
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QListWidgetItem, QTableWidgetItem, QStyle, QMessageBox, QFontDialog, QPlainTextDocumentLayout, QActionGroup, QLabel, QDockWidget, QVBoxLayout
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QMediaMetaData, QMediaRecorder, QAudioRecorder, QMultimedia, QVideoEncoderSettings, QAudioEncoderSettings
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QFile, QTextStream, QUrl, QTime, QDateTime, QSettings, QRegExp, QSize
_ = lambda txt: QtCore.QCoreApplication.translate("PloverCAT", txt)

import plover
from plover.config import Config, DictionaryConfig
from plover.engine import StenoEngine
from plover.steno import Stroke
from plover.dictionary.base import load_dictionary
from plover import log

from plover_cat.plover_cat_ui import Ui_PloverCAT
from plover_cat.rtf_parsing import steno_rtf

# base folder/
#     dictionaries/
#         transcript.json
#         custom.json
#         dictionaries_backup
#     styles/
#         default.json
#     audio/
#     transcript.transcript
#     transcript.tape
#     transcript.config

re_strokes = re.compile(r"\s\s>{1,5}(.*)$")
steno_untrans = re.compile(r"(?=[STKPWHRAO*EUFBLGDZ])S?T?K?P?W?H?R?A?O?\*?E?U?F?R?P?B?L?G?T?S?D?Z?")

default_styles = {
    "Normal": {
        "family": "paragraph",
        "nextstylename": "Normal",
        "textproperties": {
            "fontfamily": "Courier New",
            "fontname": "'Courier New'",
            "fontsize": "12pt"
        },
        "paragraphproperties": {
            "linespacing": "200%"
        }
    },
    "Question": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Answer",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Answer": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Question",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Colloquy": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",  
        "paragraphproperties": {
            "textindent": "1.5in"
        }     
    },
    "Quote": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal", 
        "paragraphproperties": {
            "marginleft": "1in",
            "textindent": "0.5in"
        } 
    },
    "Parenthetical": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",
        "paragraphproperties": {
            "marginleft": "1.5in"
        }        
    }
}

default_config = {
    "base_directory": "",
    "style": "styles/default.json",
    "dictionaries": [],
    "page_width": "8.5",
    "page_height": "11",
    "page_left_margin": "1.75",
    "page_top_margin": "0.7874",
    "page_right_margin": "0.3799",
    "page_bottom_margin": "0.7874",
    "page_line_numbering": False
}
# shortcuts based on windows media player
default_dict = {
    "S-FRLG":"{#control(s)}", # save
    "P-FRLG":"{#control(p)}", # play/pause
    "W-FRLG":"{#control(w)}", # audio stop
    "HR-FRLG":"{#control(l)}", # skip back
    "SKWR-FRLG":"{#control(j)}", # skip forward
    "KR-FRLG":"{#control(c)}", # copy
    "SR-FRLG":"{#control(v)}", # paste
    "KP-FRLG":"{#control(x)}", # cut
    "TP-FRLG":"{#control(f)}", # find
    "TKPW-FRLGS":"{#control(shift(g))}", # speed up
    "S-FRLGS":"{#control(shift(s))}", # slow down
    "STKPW-FRLG":"{#controls(z)}", # undo
    "KWR-FRLG":"{#controls(y)}" # redo
    # "-FRLG":"{#controls()}", FRLGS for ctrol + shift
    # "-PSZ":"{#control()}" alternative template with PSZ, FPSZ for control + shift
}

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

def add_custom_dicts(custom_dict_paths, dictionaries):
    """Takes list of dictionary paths, returns Plover dict config"""
    dictionaries = dictionaries[:]
    custom_dicts = [DictionaryConfig(path, True) for path in custom_dict_paths]
    return custom_dicts + dictionaries

## copied from plover_dict_commands
def load_dictionary_stack_from_backup(path):
    """Restore Plover dicts from backup file."""
    try:
        with open(path, 'r') as f:
            try:
                dictionaries = json.load(f)
            except json.JSONDecodeError:
                dictionaries = None
        if dictionaries:
            old_dictionaries = [DictionaryConfig.from_dict(x) for x in dictionaries]
            os.remove(path) #backup recovered, delete file
            return old_dictionaries
        else:
            return None
    except IOError:
        return None

def backup_dictionary_stack(dictionaries, path):
    """Takes Plover dict config, creates backup file."""
    log.info("Backing up Plover dictionaries to %s", path)
    if dictionaries:
        with open(path, 'w') as f:
            json.dump([DictionaryConfig.to_dict(d) for d in dictionaries], f)
    else:
        try:
            os.remove(path)
        except OSError:
            pass

def ms_to_hours(millis):
    """Converts milliseconds to formatted hour:min:sec.milli"""
    seconds, milliseconds = divmod(millis, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return ("%02d:%02d:%02d.%03d" % (hours, minutes, seconds, milliseconds))

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

def remove_strings(stroke_data, backspace):
    """Mimics backspaces on stroke data

    Arg:
        stroke_data (list): list of steno stroke elements in
            [time, steno_strokes, translation, ...] format
        backspace (int): number of backspaces
        
    Returns:
        List of steno strokes, with # of backspaces removed from end 

    """
    stroke_data = stroke_data[:]
    if len(stroke_data) > 0:
        if not all(isinstance(el, list) for el in stroke_data):
            stroke_data = [stroke_data]
    backspace = backspace
    if len(stroke_data) == 1:
        stroke = stroke_data[0]
        if backspace >= len(stroke[2]):
            return []
        else:
            string = stroke[2]
            string = string[:-backspace]
            stroke[2] = string
            return [stroke]     
    for stroke in reversed(stroke_data[:]):
        stroke = stroke[:]
        stroke_data.remove(stroke)
        if backspace >= len(stroke[2]):
            backspace = backspace - len(stroke[2])
            # backspace == 0 should be almost all cases (* removes one-stroke word and space before/after)
            if backspace == 0: break
        else:
            string = stroke[2]
            string = string[:-backspace]
            stroke[2] = string
            stroke_data.append(stroke)
            break
    return stroke_data

def split_stroke_data(stroke_data, start):
    """Returns tuple of lists of steno strokes, split at position start.

    Args:
        stroke_data (list): list of steno stroke elements in 
            [time, steno_strokes, translation, ...] format
        start (int): position for splitting, based on text lengths in 
            the translation element of stroke

    Returns:
        tuple of two lists of steno strokes, split at the position 
            specified by the start argument based on the translation lengths. 

    """
    stroke_data = stroke_data[:]
    # hack here if stroke data only has one stroke, so not list of list
    if len(stroke_data) > 0:
        if not all(isinstance(el, list) for el in stroke_data):
            stroke_data = [stroke_data]
    split = False
    first_part = []
    second_part = []
    for stroke in stroke_data:
        start = start - len(stroke[2])
        if start > 0:
            first_part.append(stroke)
        elif start == 0:
            # special case but likely most common when split occurs at boundary of stroke
            first_part.append(stroke)
            split = True
        else:
            if split:
                second_part.append(stroke)
            else:
                text = stroke[2]
                # arbitrarily, the stroke data goes with first part if middle of split
                # the second part will still have the time
                first_part.append([stroke[0], stroke[1], text[:start]])
                second_part.append([stroke[0], "", text[start:]])
                split = True
    return first_part, second_part

def extract_stroke_data(stroke_data, start, end, copy = False):
    """Returns piece(s) of stroke data mimicking a cut

    Args:
        stroke_data (list): list of steno stroke elements in 
            [time, steno_strokes, translation, ...] format
        start (int): start of split
        end (int): end of split
        copy (boolean): whether to return part between start and end,
            or combined leftovers
    
    Returns:
        Depends on state of copy. If True, a list of stroke data,
            extracted from the stroke_data between positions start 
            and end. If False, tuple of stroke data list, 1) from 
            beginning to start position, and 2) from end position 
            to last element in stroke_data.

    """
    before, keep = split_stroke_data(stroke_data, start)
    selected, after = split_stroke_data(keep, end - start)
    left_over = before + after
    if copy:
        # only return copied part
        return selected
    else:
        # need to return selected part, but original block needs to be reset 
        return left_over, selected
            

class PloverCATWindow(QMainWindow, Ui_PloverCAT):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        # ui and widgets setup
        self.setupUi(self)
        self.player = QMediaPlayer()
        self.recorder = QAudioRecorder()
        self.player.videoAvailableChanged.connect(self.set_up_video)
        self.audio_device.addItems(self.recorder.audioInputs())
        self.audio_codec.addItems(self.recorder.supportedAudioCodecs())
        self.audio_container.addItems(self.recorder.supportedContainers())
        # no point sampling higher than 48000 or even 44100 in reality from basic computer + mic
        self.audio_sample_rate.addItems([str(rate) for rate in reversed(self.recorder.supportedAudioSampleRates()[0]) if rate < 50000])
        self.audio_channels.addItem("Default", -1)
        self.audio_channels.addItem("1-channel", 1)
        self.audio_channels.addItem("2-channel", 2)
        self.audio_channels.addItem("4-channel", 4)
        self.audio_bitrate.addItem("Default", -1)
        self.audio_bitrate.addItem("32000", 32000)
        self.audio_bitrate.addItem("64000", 64000)
        self.audio_bitrate.addItem("96000", 96000)
        self.audio_bitrate.addItem("128000", 128000)
        # vars for startup
        settings = QSettings("PloverCAT", "OpenCAT")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.contains("windowstate"):
            self.restoreState(settings.value("windowstate"))
        if settings.contains("windowfont"):
            font_string = settings.value("windowfont")
            font = QFont()
            font.fromString(font_string)
            self.setFont(font)
        self.config = {}
        self.file_name = ""
        self.styles = {}
        self.styles_path = ""
        self.stroke_time = ""
        self.audio_file = ""
        self.cursor_block = 0
        self.cursor_block_position = 0
        self.last_raw_steno = ""
        self.last_string_sent = ""
        self.last_backspaces_sent = 0
        self.cutcopy_storage = {}
        self.last_action = deque(maxlen = 10)
        self.redone_action = deque(maxlen = 10)
        self.textEdit.setPlainText("Welcome to PloverCAT\nOpen or create a translation folder first with File->New...\n A dated transcript folder will be created.")
        self.menu_enabling()
        # connections:
        ## file setting/saving
        self.actionQuit.triggered.connect(lambda: self.action_close())
        self.actionNew.triggered.connect(lambda: self.create_new())
        self.actionClose.triggered.connect(lambda: self.close_file())
        self.actionOpen.triggered.connect(lambda: self.open_file())
        self.actionSave.triggered.connect(lambda: self.save_file())
        self.actionSave_As.triggered.connect(lambda: self.save_as_file())
        self.actionWindowFont.triggered.connect(lambda: self.change_window_font())
        self.actionPlainText.triggered.connect(lambda: self.export_text())
        self.actionASCII.triggered.connect(lambda: self.export_ascii())
        self.actionSubRip.triggered.connect(lambda: self.export_srt())
        self.actionODT.triggered.connect(lambda: self.export_odt())
        self.actionOpen_Transcript_Folder.triggered.connect(lambda: self.open_root())
        self.actionImport_RTF.triggered.connect(lambda: self.import_rtf())
        ## audio connections
        self.actionOpen_Audio.triggered.connect(lambda: self.open_audio())
        self.actionPlay_Pause.triggered.connect(self.play_pause)
        self.actionStop_Audio.triggered.connect(self.stop_play)
        self.playRate.valueChanged.connect(self.update_playback_rate)
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_seeker_track)
        self.audio_seeker.sliderMoved.connect(self.set_position)
        self.actionSkip_Forward.triggered.connect(lambda: self.seek_position())
        self.actionSkip_Back.triggered.connect(lambda: self.seek_position(-1))
        self.actionRecord_Pause.triggered.connect(lambda: self.record_or_pause())
        self.actionStop_Recording.triggered.connect(lambda: self.stop_record())
        self.recorder.error.connect(lambda: self.recorder_error())
        self.recorder.durationChanged.connect(self.update_record_time)
        self.actionShow_Video.triggered.connect(lambda: self.show_hide_video())
        ## editor/plover related connections
        self.textEdit.cursorPositionChanged.connect(self.display_block_data)
        self.editorCheck.stateChanged.connect(self.editor_lock)
        self.submitEdited.clicked.connect(self.edit_user_data)
        self.actionMerge_Paragraphs.triggered.connect(lambda: self.merge_paragraphs())
        self.actionSplit_Paragraph.triggered.connect(lambda: self.split_paragraph())
        self.actionCopy.triggered.connect(lambda: self.copy_steno())
        self.actionCut.triggered.connect(lambda: self.cut_steno())
        self.actionPaste.triggered.connect(lambda: self.paste_steno())
        self.actionRedo.triggered.connect(lambda: self.redo_action())
        self.actionUndo.triggered.connect(lambda: self.undo_action())
        self.actionFind_Replace_Pane.triggered.connect(lambda: self.show_find_replace())
        self.actionAdd_Custom_Dict.triggered.connect(lambda: self.add_dict())
        self.actionRemove_Transcript_Dict.triggered.connect(lambda: self.remove_dict())
        ## style connections
        self.edit_page_layout.clicked.connect(self.update_config)
        self.style_file_select.clicked.connect(self.select_style_file)
        self.style_selector.activated.connect(self.update_paragraph_style)
        ## search/replace connections
        self.search_text.toggled.connect(lambda: self.search_text_options())
        self.search_steno.toggled.connect(lambda: self.search_steno_options())
        self.search_untrans.toggled.connect(lambda: self.search_untrans_options())
        self.search_forward.clicked.connect(lambda: self.search())
        self.search_backward.clicked.connect(lambda: self.search(-1))
        self.replace_selected.clicked.connect(lambda: self.replace())
        self.replace_all.clicked.connect(lambda: self.replace_everything())
        ## tape
        self.textEdit.blockCountChanged.connect(lambda: self.get_tapey_tape())
        self.textEdit.blockCountChanged.connect(lambda: self.to_next_style())
        self.suggest_sort.toggled.connect(lambda: self.get_tapey_tape())
        self.numbers = {number: letter for letter, number in plover.system.NUMBERS.items()}
        ## engine connections
        engine.signal_connect("stroked", self.on_stroke) 
        engine.signal_connect("stroked", self.log_to_tape) 
        engine.signal_connect("send_string", self.on_send_string)
        engine.signal_connect("send_backspaces", self.count_backspaces)
        self.statusBar.showMessage("Create New Transcript or Open Existing...")
        self.cursor_status = QLabel("Par,Char: {line},{char}".format(line = 0, char = 0))
        self.cursor_status.setObjectName("cursor_status")
        self.statusBar.addPermanentWidget(self.cursor_status)
        log.info("Main window open")

    def menu_enabling(self, value = True):
        self.actionNew.setEnabled(value)
        self.actionSave.setEnabled(not value)
        self.actionSave_As.setEnabled(not value)
        self.actionOpen.setEnabled(value)
        self.actionPlainText.setEnabled(not value)
        self.actionASCII.setEnabled(not value)
        self.actionSubRip.setEnabled(not value)
        self.actionODT.setEnabled(not value)
        self.actionAdd_Custom_Dict.setEnabled(not value)
        self.actionMerge_Paragraphs.setEnabled(not value)
        self.actionSplit_Paragraph.setEnabled(not value)
        self.actionPlay_Pause.setEnabled(not value)
        self.actionStop_Audio.setEnabled(not value)
        self.actionRecord_Pause.setEnabled(not value)
        self.menuAudio.setEnabled(not value)
        self.menuEdit.setEnabled(not value)
        self.actionOpen_Transcript_Folder.setEnabled(not value)
        self.actionImport_RTF.setEnabled(not value)
    # open/close/save
    def create_new(self):
        ## make new dir, sets gui input
        project_dir = QFileDialog.getExistingDirectory(self, "Select Directory", os.getcwd())
        if not project_dir:
            log.info("No directory selected, passing")
            return
        log.info("Selected directory for new project.")
        project_dir = pathlib.Path(project_dir)
        transcript_dir_name = "transcript-" + datetime.now().strftime("%Y-%m-%dT%H%M%S")
        transcript_dir_path = project_dir / transcript_dir_name
        log.info("Project directory:" + str(transcript_dir_path))
        os.mkdir(transcript_dir_path)
        self.file_name = transcript_dir_path
        config_path = transcript_dir_path / "config.CONFIG"
        plover_engine_config = self.engine.config
        attach_space = plover_engine_config["space_placement"]
        default_config["space_placement"] = attach_space
        self.config = default_config
        with open(config_path, "w") as f:
            json.dump(default_config, f)
            log.info("Project configuration file created")
        self.create_default_styles()
        style_file_name = transcript_dir_path / "styles/default.json"
        self.styles = self.load_check_styles(style_file_name)
        default_dict_path = transcript_dir_path / "dict"
        self.create_default_dict()
        self.textEdit.clear()
        self.strokeList.clear()
        self.suggestTable.clearContents()
        self.menu_enabling(False)
        self.statusBar.showMessage("Created project at {filename}".format(filename = str(self.file_name)))
        log.info("New project successfully created and set up")

    def open_file(self):
        name = "Config"
        extension = "config"
        selected_folder = QFileDialog.getOpenFileName( self, _("Open " + name), os.getcwd(), _(name + "(*." + extension + ")"))[0]
        if not selected_folder:
            log.info("No config file was selected for loading.")
            return
        selected_folder = pathlib.Path(selected_folder).parent
        ## one day, a modal here to make sure non-empty textedit saved before switching to existing file
        self.statusBar.showMessage("Opening project at {filename}".format(filename = str(selected_folder)))
        log.info("Loading project files from %s", str(selected_folder))
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")
        transcript_tape = selected_folder.joinpath(selected_folder.stem).with_suffix(".tape")
        self.file_name = selected_folder
        config_contents = self.load_config_file(selected_folder)
        log.debug("Config contents: %s", config_contents)
        self.config = config_contents
        self.textEdit.clear()
        self.strokeList.clear()
        self.suggestTable.clearContents()
        style_path = selected_folder / config_contents["style"]
        log.info("Loading styles for transcript")
        self.styles = self.load_check_styles(style_path)
        self.set_dictionary_config(config_contents["dictionaries"])
        current_cursor = self.textEdit.textCursor()
        if pathlib.Path(transcript_tape).is_file():
            log.info("Tape file found, loading.")
            self.statusBar.showMessage("Loading tape at {filename}".format(filename = str(transcript_tape)))
            tape_file = QFile(str(transcript_tape))
            tape_file.open(QFile.ReadOnly|QFile.Text)
            istream = QTextStream(tape_file)
            self.strokeList.document().setPlainText(istream.readAll())
            self.strokeList.verticalScrollBar().setValue(self.strokeList.verticalScrollBar().maximum())
            log.info("Loaded tape.")
        if pathlib.Path(transcript).is_file():
            log.info("Transcript file found, loading")
            with open(transcript, "r") as f:
                self.statusBar.showMessage("Reading transcript data at {filename}".format(filename = str(transcript)))
                json_document = json.loads(f.read())
            new_document = QTextDocument()
            new_document.setDocumentLayout(QPlainTextDocumentLayout(new_document))
            document_cursor = QTextCursor(new_document)
            self.statusBar.showMessage("Loading transcript data at {filename}".format(filename = str(transcript)))
            for key, value in json_document.items():
                document_cursor.insertText(value["text"])
                block_data = BlockUserData()
                for k, v in value["data"].items():
                    block_data[k] = v
                document_cursor.block().setUserData(block_data)
                if "\n" in block_data["strokes"][-1][2]:
                    document_cursor.insertText("\n")
            current_cursor.movePosition(QTextCursor.End)
            self.textEdit.setDocument(new_document)
            self.textEdit.moveCursor(QTextCursor.End)
            self.statusBar.showMessage("Finished loading transcript data at {filename}".format(filename = str(transcript)))
            log.info("Loaded transcript.")
        self.menu_enabling(False) 
        ## manually set first block data  
        new_block = self.textEdit.document().firstBlock()
        if not new_block.userData():
            block_dict = BlockUserData()
            block_dict["creationtime"] = datetime.now().isoformat("T", "milliseconds")
            new_block.setUserData(block_dict)
        log.info("Project files, if exist, have been loaded.")
        self.statusBar.showMessage("Setup complete. Ready for work.")     

    def save_file(self):
        if not self.file_name:
            log.info("No project dir set, cannot save file.")
            return
        selected_folder = pathlib.Path(self.file_name)
        self.update_config()
        document_blocks = self.textEdit.document().blockCount()
        json_document = {}
        log.info("Extracting block data for transcript save")
        self.statusBar.showMessage("Saving transcript data at {filename}".format(filename = str(selected_folder)))
        for i in range(document_blocks):
            block = self.textEdit.document().findBlockByNumber(i)
            block_dict = block.userData().return_all()
            block_text = block.text()
            block_num = i
            inner_dict =  {"text": block_text, "data": block_dict}
            log.debug(inner_dict)
            json_document[block_num] = inner_dict
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")
        log.info("Saved transcript data to %s", str(transcript))
        with open(transcript, "w") as f:
            json.dump(json_document, f)
            log.info("Transcript data successfully saved")
        self.textEdit.document().setModified(False) 
        self.statusBar.showMessage("Saved project data at {filename}".format(filename = str(selected_folder)))  

    def save_as_file(self):
        ## select dir and save tape and file to different location, path is then set to new location
        name = "Existing Transcript"
        selected_folder = QFileDialog.getExistingDirectory(
            self,
            _("Save" + name + "as ..."),
            str(self.file_name))
        if not selected_folder:
            log.info("No directory selected, skipping save.")
            return
        selected_folder = pathlib.Path(selected_folder)
        transcript_dir_name = pathlib.Path("transcript-" + datetime.now().strftime("%Y-%m-%dT%H%M%S"))
        transcript_dir_path = selected_folder / transcript_dir_name
        os.mkdir(transcript_dir_path)
        tape_contents = self.strokeList.document().toPlainText()
        transcript = transcript_dir_path.joinpath(transcript_dir_path.stem).with_suffix(".transcript")
        transcript_tape = transcript_dir_path.joinpath(transcript_dir_path.stem).with_suffix(".tape")
        document_blocks = self.textEdit.document().blockCount()
        json_document = []
        log.info("Extracting block data for transcript save")
        self.statusBar.showMessage("Saving transcript data at {filename}".format(filename = str(selected_folder)))
        for i in range(document_blocks):
            block = self.textEdit.document().findBlockByNumber(i)
            block_dict = block.userData().return_all()
            block_text = block.text()
            block_num = i
            inner_dict =  {"text": block_text, "data": block_dict}
            json_element = {block_num: inner_dict}
            log.debug(json_element)
            json_document.append(json_element)        
        with open(transcript, "w") as f:
            json.dump(json_document, f)
            log.info("Transcript data saved in new location" + str(transcript))
        with open(transcript_tape, "w") as f:
            f.write(tape_contents)
            log.info("Tape data saved in new location" + str(transcript_tape))
        self.file_name = transcript_dir_path
        self.setWindowTitle(str(self.file_name))
        self.textEdit.document().setModified(False)
        self.statusBar.showMessage("Saved transcript data at {filename}".format(filename = str(selected_folder)))

    def close_file(self):
        if self.textEdit.document().isModified():
            user_choice = QMessageBox.question(self, "Close", "Are you sure you want to close without saving changes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.info("User choice to close without saving")
                pass
            else:
                log.info("Abort project close because of unsaved changes.")
                return
        # restore dictionaries back to original
        self.restore_dictionary_from_backup()
        if self.recorder.status() == QMediaRecorder.RecordingState:
            self.stop_record()
        ## resets textedit and vars
        self.file_name = ""
        self.cursor_block = 0
        self.cursor_block_position = 0        
        self.menu_enabling()
        self.textEdit.setPlainText("Welcome to PloverCAT\nSet up or create a translation folder first with File->New...\n A dated transcript folder will be created.")        
        self.strokeList.clear()
        self.suggestTable.clearContents()
        self.statusBar.showMessage("Project closed")

    def action_close(self):
        log.info("User selected quit.")
        settings = QSettings("PloverCAT", "OpenCAT")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowstate", self.saveState())
        settings.setValue("windowfont", self.font().toString())
        log.info("Saved window settings")
        self.close_file()
        log.info("Closing window.")
        self.parent().close()

    def open_root(self):
        selected_folder = pathlib.Path(self.file_name)
        log.info("Attempting to open file directory %s", str(selected_folder))
        if platform.startswith("win"):
            os.startfile(selected_folder)
        elif platform.startswith("linux"):
            subprocess.call(['xdg-open', selected_folder])
        elif platform.startswith("darwin"):
            subprocess.call(['open', selected_folder])
        else:
            log.info("Unknown platform. Not opening folder directory.")
            self.textEdit.statusBar.setMessage("Unknown operating system. Not opening file directory.")
    # dict related
    def create_default_dict(self):
        log.info("Create default transcript dictionary.")
        selected_folder = self.file_name
        dict_dir = selected_folder / "dict"
        log.info("Create dict directory if not present.")
        try:
            os.mkdir(dict_dir)
        except FileExistsError:
            pass
        dict_file_name = "default.json"
        dict_file_name = dict_dir / dict_file_name
        with open(dict_file_name, "w") as f:
            json.dump(default_dict, f)
            log.info("Default dictionary created in %s", str(dict_file_name))
        self.set_dictionary_config([str(dict_file_name.relative_to(selected_folder))])

    def add_dict(self):
        ## select a dict from not file location to add to plover stack
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Dictionary"),
            str(self.file_name), _("Dict (*.json)"))[0]
        if not selected_file:
            return
        selected_file = pathlib.Path(selected_file)
        log.info("Selected dictionary at %s to add.", str(selected_file))
        dict_dir_path = self.file_name / "dict"
        log.info("Create dict directory if not present.")
        try:
            os.mkdir(dict_dir_path)
        except FileExistsError:
            pass
        dict_dir_name = dict_dir_path / selected_file.name
        if selected_file != dict_dir_name:
            log.info("Copying dictionary at %s to %s", str(selected_file), str(dict_dir_name))
            copyfile(selected_file, dict_dir_name)
        list_dicts = self.engine.config["dictionaries"]
        # do not add if already in dict
        if str(selected_file) in list_dicts:
            log.info("Selected dictionary is already in loaded dictionaries, passing.")
            return
        new_dict_config = add_custom_dicts([str(selected_file)], list_dicts)
        self.engine.config = {'dictionaries': new_dict_config}
        # update config
        config_contents = self.config
        dictionary_list = config_contents["dictionaries"]
        log.debug("Loaded dictionary objects: %s", dictionary_list)
        dictionary_list.append(str(dict_dir_name.relative_to(self.file_name)))
        config_contents["dictionaries"] = dictionary_list
        log.info("Add %s to config", str(dict_dir_name.relative_to(self.file_name)))
        self.config = config_contents
        self.update_config()

    def remove_dict(self):
        dict_dir_path = self.file_name / "dict"
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Dictionary to remove"),
            str(dict_dir_path), _("Dict (*.json)"))[0]
        if not selected_file:
            return
        selected_file = pathlib.Path(selected_file)
        log.info("Selected dictionary at %s to remove.", str(selected_file))
        config_contents = self.config
        dictionary_list = config_contents["dictionaries"]
        list_dicts = self.engine.config["dictionaries"]
        list_dicts = [i.path for i in list_dicts if pathlib.Path(i.path)  != selected_file]
        new_dict_config = add_custom_dicts(list_dicts, [])
        self.engine.config = {'dictionaries': new_dict_config}
        if str(selected_file.relative_to(self.file_name)) in dictionary_list:
            dictionary_list = [i for i in dictionary_list if i != str(selected_file.relative_to(self.file_name))]
            log.info("Remove %s from config", str(selected_file.relative_to(self.file_name)))
            config_contents["dictionaries"] = dictionary_list
            self.config = config_contents
            self.update_config()
        else:
            log.info("Selected dictionary not a transcript dictionary, passing.")

    def set_dictionary_config(self, dictionaries = None):
        # dictionaries must be passed in as list, or bad things happen
        # these dictionaries should have the relative paths to root folder
        log.info("Setting and loading dictionar(ies)")
        plover_config = self.engine.config
        list_dicts = plover_config["dictionaries"]
        default_dict_path = self.file_name / "dict" / "default.json"
        if not default_dict_path.exists():
            log.info("Default dict does not exist. Creating default.")
            self.create_default_dict()
        backup_dict_path = self.file_name / "dict" / "dictionaries_backup"
        backup_dictionary_stack(list_dicts, backup_dict_path)
        full_paths = [str(self.file_name / pathlib.Path(i)) for i in dictionaries]
        log.debug("Trying to load dictionaries at %s", full_paths)
        if any(new_dict in list_dicts for new_dict in full_paths):
            log.info("Checking for duplicate dictionaries with loaded dictionaries.")
            # if any of the new dicts are already in plover
            set_full_paths = set(full_paths)
            set_list_dicts = set(list_dicts)
            full_paths = list(set_full_paths.difference(set_list_dicts))
            dictionaries = [pathlib.Path(i).relative_to(self.file_name) for i in full_paths]
        new_dict_config = add_custom_dicts(full_paths, list_dicts)
        self.engine.config = {'dictionaries': new_dict_config}
        config_dict = self.config
        config_dict["dictionaries"] = list(set(config_dict["dictionaries"] + dictionaries))
        self.update_config()

    def restore_dictionary_from_backup(self):
        selected_folder = pathlib.Path(self.file_name)
        log.info("Attempting to restore dictionaries configuration from backup.")
        backup_dictionary_location = selected_folder / "dict" / "dictionaries_backup"
        log.info("Backup file location: %s", str(backup_dictionary_location))
        if backup_dictionary_location.exists():
            restored_dicts = load_dictionary_stack_from_backup(backup_dictionary_location)
            self.engine.config = {'dictionaries': restored_dicts}
            log.info("Dictionaries restored from backup file.")
    # config related
    def load_config_file(self, dir_path):
        config_path = pathlib.Path(dir_path) / "config.CONFIG"
        log.info("Loading configuration file:" + str(config_path))
        with open(config_path, "r") as f:
            config_contents = json.loads(f.read())
        log.debug(config_contents)
        self.page_width.setValue(float(config_contents["page_width"]))
        self.page_height.setValue(float(config_contents["page_height"]))
        self.page_left_margin.setValue(float(config_contents["page_left_margin"]))
        self.page_top_margin.setValue(float(config_contents["page_top_margin"]))
        self.page_right_margin.setValue(float(config_contents["page_right_margin"]))
        self.page_bottom_margin.setValue(float(config_contents["page_bottom_margin"]))
        self.enable_line_num.setChecked(config_contents["page_line_numbering"])
        log.info("Configuration successfully loaded.")
        return config_contents

    def update_config(self):
        log.info("User update config.")
        config_contents = self.config
        style_path = pathlib.Path(self.styles_path)
        config_contents["style"] = str(style_path.relative_to(self.file_name))
        config_contents["page_width"] = self.page_width.value()
        config_contents["page_height"] = self.page_height.value()
        config_contents["page_left_margin"] = self.page_left_margin.value()
        config_contents["page_top_margin"] = self.page_top_margin.value()
        config_contents["page_right_margin"] = self.page_right_margin.value()
        config_contents["page_bottom_margin"] = self.page_bottom_margin.value()
        config_contents["page_line_numbering"] = self.enable_line_num.isChecked()
        self.config = config_contents
        log.debug(config_contents)
        self.save_config(self.file_name)

    def save_config(self, dir_path):
        config_path = pathlib.Path(dir_path) / "config.CONFIG"
        log.info("Saving config to " + str(config_path))
        config_contents = self.config
        with open(config_path, "w") as f:
            json.dump(config_contents, f)
            log.info("Config saved")
            self.statusBar.showMessage("Saved config data in {filename}".format(filename = str(config_path)))
    # style related
    def create_default_styles(self):
        log.info("Create default styles for project")
        selected_folder = self.file_name
        style_dir = selected_folder / "styles"
        try:
            os.mkdir(style_dir)
        except FileExistsError:
            pass
        style_file_name = "default.json"
        style_file_name = style_dir / style_file_name
        with open(style_file_name, "w") as f:
            json.dump(default_styles, f)
            log.info("Default styles set in " + str(style_file_name))

    def load_check_styles(self, path):
        path = pathlib.Path(path)
        if not path.exists():
            # go to default if the config style doesn't exist
            log.info("Config style file does not exist. Loading default.")
            path = self.file_name / "styles" / "default.json"
            if not path.exists():
                # if default somehow got deleted
                self.create_default_styles()
        if path.suffix == ".odt":
            log.info("Loading ODF style file from %s", str(path))
            style_text = load(path)
            self.style_selector.clear()
            json_styles = {}
            for style in style_text.getElementsByType(Style):
                json_styles[style.getAttribute("name")] = {"family": style.getAttribute("family"), "nextstylename": style.getAttribute("nextstylename")}
            log.debug(json_styles)
        else:
            log.info("Loading JSON style file from %s", str(path))
            # this only checks first level keys, one day, should use the data from this [attribute[1] for attribute in Style(name = "Name").allowed_attributes()],  [attribute[1] for attribute in TextProperties().allowed_attributes()], [attribute[1] for attribute in ParagraphProperties().allowed_attributes()] 
            acceptable_keys = {'autoupdate', 'class', 'datastylename', 'defaultoutlinelevel', 'displayname', 'family', 'listlevel', 'liststylename', 'masterpagename', 'name', 'nextstylename', 'parentstylename', 'percentagedatastylename', "paragraphproperties", "textproperties"}
            with open(path, "r") as f:
                json_styles = json.loads(f.read())
            log.debug(json_styles)
            for k, v in json_styles.items():
                sub_keys = set([*v])
                if not sub_keys.issubset(acceptable_keys):
                    log.info("Some first-level keys in style json are not valid.")
                    self.statusBar.showMessage("First level keys in {filepath} for style {style} should be one of:{keys}".format(filepath = str(path), style = k, keys = acceptable_keys))
                    return False
        # clear old styles out before loading from new styles
        self.style_selector.clear()
        self.style_selector.addItems([*json_styles])
        self.statusBar.showMessage("Loaded style data from {filename}".format(filename = str(path)))
        log.info("Styles loaded.")
        original_style_path = path
        new_style_path = self.file_name / "styles" / original_style_path.name
        if original_style_path != new_style_path:
            log.info("Copying style file at %s to %s", original_style_path, new_style_path)
            copyfile(original_style_path, new_style_path)
        self.styles_path = new_style_path
        self.style_file_path.setText(path.name)
        self.update_config()
        return json_styles

    def select_style_file(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Style JSON or odt"),
            str(self.file_name), _("Style (*.json *.odt)"))[0]
        if not selected_file:
            return
        log.info("User selected style file at %s", selected_file)
        self.styles = self.load_check_styles(selected_file)

    def change_window_font(self):
        font, valid = QFontDialog.getFont()
        if valid:
            self.setFont(font)
            log.info("Font set for window")       

    def display_block_data(self):
        current_cursor = self.textEdit.textCursor()
        block_number = current_cursor.blockNumber()
        block_data = current_cursor.block().userData()
        if not block_data:
            return
        self.editorParagraphLabel.setText(str(block_number))
        if block_data["creationtime"]:
            self.editorCreationTime.setDateTime(QDateTime.fromString(block_data["creationtime"],  "yyyy-MM-ddTHH:mm:ss.zzz"))
        if block_data["edittime"]:
            self.editorEditTime.setDateTime(QDateTime.fromString(block_data["edittime"],  "yyyy-MM-ddTHH:mm:ss.zzz"))
        if block_data["audiostarttime"]:
            self.editorAudioStart.setTime(QTime.fromString(block_data["audiostarttime"], "HH:mm:ss.zzz"))
        if block_data["audioendtime"]:
            self.editorAudioEnd.setTime(QTime.fromString(block_data["audioendtime"], "HH:mm:ss.zzz"))
        if block_data["style"]:
            self.style_selector.setCurrentText(block_data["style"])
        self.cursor_status.setText("Par,Char: {line},{char}".format(line = block_number, char = current_cursor.positionInBlock())) 

    def update_paragraph_style(self):
        # this only activates for user interaction
        focus_block = self.textEdit.document().findBlockByNumber(self.cursor_block)
        block_dict = focus_block.userData()
        if not block_dict:
            block_dict = BlockUserData()
        selected_style = self.style_selector.currentText()
        block_dict = update_user_data(block_dict, key = "style", value = selected_style)
        log.info("Set paragraph style.")
        log.debug(block_dict.return_all())
        self.statusBar.showMessage("Update paragraph {block_num} style to {style}".format(block_num = self.cursor_block, style = str(selected_style)))
        focus_block.setUserData(block_dict)

    def to_next_style(self):
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.blockNumber()
        if current_block == 0:
            return
        focus_block = self.textEdit.document().findBlockByNumber(current_block)
        block_dict = focus_block.userData()
        if not block_dict:
            block_dict = BlockUserData()
        style_data = self.styles
        if len(style_data) == 0:
            return
        # use the first style as default if nothing is set
        previous_style = None
        new_style = [*style_data][0]
        previous_block = focus_block.previous()
        if previous_block:
            previous_dict = previous_block.userData()
            previous_style = previous_dict["style"]
        if previous_style:
            new_style = style_data[previous_style]["nextstylename"]
        block_dict = update_user_data(block_dict, key = "style", value = new_style)
        self.style_selector.setCurrentText(new_style)
        focus_block.setUserData(block_dict)
        self.statusBar.showMessage("Paragraph style set to {style}".format(style = new_style))

    def editor_lock(self):
        if self.editorCheck.isChecked():
            self.submitEdited.setEnabled(False)
        else:
            self.submitEdited.setEnabled(True)

    def edit_user_data(self):
        self.submitEdited.setEnabled(False)
        self.editorCheck.setChecked(True)
        block_data = self.textEdit.document().findBlockByNumber(self.cursor_block).userData()
        block_data["creationtime"] = self.editorCreationTime.dateTime().toString(Qt.ISODateWithMs)
        if self.editorEditTime.dateTime().toString(Qt.ISODateWithMs) != "2000-01-01T00:00:00.000":
            block_data["edittime"] = self.editorEditTime.dateTime().toString(Qt.ISODateWithMs)
        block_data["edittime"] = self.editorEditTime.dateTime().toString(Qt.ISODateWithMs)
        if self.editorAudioStart.time().toString(Qt.ISODateWithMs) != "00:00:00.000":
            block_data["audiostarttime"] = self.editorAudioStart.time().toString(Qt.ISODateWithMs)
        if self.editorAudioEnd.time().toString(Qt.ISODateWithMs) != "00:00:00.000":
            block_data["audioendtime"] = self.editorAudioEnd.time().toString(Qt.ISODateWithMs)
        if self.editorNotes.text():
            block_data["notes"] = self.editorNotes.text()
        log.info("Updating block data for %d", self.cursor_block)
        log.debug(block_data.return_all())
        self.textEdit.document().findBlockByNumber(self.cursor_block).setUserData(block_data)
        self.statusBar.showMessage("Updated paragraph {par_num} data".format(par_num = self.cursor_block))
    # engine hooked functions
    def on_send_string(self, string):
        log.debug("Plover engine sent string: %s", string)
        self.last_string_sent = string

    def count_backspaces(self, backspace):
        log.debug("Plover engine sent %d backspace(s)", backspace)
        self.last_backspaces_sent = backspace

    def log_to_tape(self, stroke):
        # logging stroke code
        # do not log if not "typing" into window
        if not self.textEdit.isActiveWindow():
            return
        ## copy from parts of plover paper tape and tapeytape
        keys = set()
        for key in stroke.steno_keys:
            if key in self.numbers:
                keys.add(self.numbers[key])
                keys.add(plover.system.NUMBER_KEY)
            else:
                keys.add(key)
        steno = ''.join(key.strip('-') if key in keys else ' ' for key in plover.system.KEYS)
        audio_time = ''
        if self.player.state() == QMediaPlayer.PlayingState:
            real_time = self.player.position() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        if self.recorder.state() == QMediaRecorder.RecordingState:
            real_time = self.recorder.duration() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        log_string = "{0}|{1}|({2},{3})|{4}".format(self.stroke_time, audio_time, self.cursor_block, self.cursor_block_position, steno)
        self.strokeList.appendPlainText(log_string)
        if not self.file_name:
            return
        selected_folder = pathlib.Path(self.file_name)
        if selected_folder:
            transcript_tape = selected_folder.joinpath(selected_folder.stem).with_suffix(".tape")
            with open(transcript_tape, "a") as f:
                f.write(log_string)
                f.write("\n") 
                
    def get_tapey_tape(self):
        ## from tapeytape default, maybe make selectable in future?
        config_dir = pathlib.Path(plover.oslayer.config.CONFIG_DIR)
        tapey_tape_location = config_dir.joinpath('tapey_tape.txt')
        log.info("Trying to load tapey tape from default location")
        stroke_search = [re.findall(re_strokes,line) for line in open(tapey_tape_location)]
        stroke_search = [x[0] for x in stroke_search if x]
        ## number maybe adjusted in future? both number of occurrences and number of words to place into table
        ## this uses frequency order
        if self.suggest_sort.isChecked():
            most_common_strokes = [word for word, word_count in Counter(stroke_search).items() if word_count > 2]
            most_common_strokes = most_common_strokes[:min(11, len(most_common_strokes) + 1)]
            most_common_strokes = most_common_strokes[::-1]
        else: 
            most_common_strokes= [word for word, word_count in Counter(stroke_search).most_common(10) if word_count > 2]
        first_stroke = [stroke.split()[0] for stroke in most_common_strokes]
        words = [self.engine.lookup(tuple(stroke.split("/"))) for stroke in first_stroke]
        self.suggestTable.clearContents()
        self.suggestTable.setRowCount(len(words))
        self.suggestTable.setColumnCount(2)
        for row in range(len(words)):
            self.suggestTable.setItem(row, 0, QTableWidgetItem(words[row]))
            self.suggestTable.setItem(row, 1, QTableWidgetItem(most_common_strokes[row]))
        self.suggestTable.resizeColumnsToContents()
    # steno functions
    def on_stroke(self, stroke_pressed):
        self.editorCheck.setChecked(True)
        if not self.engine.output:
            return
        if not self.file_name:
            return
        # do nothing if window not in focus
        if not self.textEdit.isActiveWindow():
            return
        # insert 
        current_cursor = self.textEdit.textCursor()
        # always keep cursor at end of document
        # current_cursor.movePosition(QTextCursor.End)
        self.cursor_block = self.textEdit.textCursor().blockNumber()
        self.cursor_block_position = self.textEdit.textCursor().positionInBlock()
        # gather all variables to be logged into stroke
        self.stroke_time = datetime.now().isoformat("T", "milliseconds")
        self.last_raw_steno = stroke_pressed.rtfcre
        raw_steno = self.last_raw_steno
        string_sent = self.last_string_sent
        backspaces_sent = self.last_backspaces_sent
        if self.player.state() == QMediaPlayer.PlayingState:
            real_time = self.player.position() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        elif self.recorder.state() == QMediaRecorder.RecordingState:
            real_time = self.recorder.duration() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        focus_block = self.textEdit.document().findBlockByNumber(self.cursor_block)
        ## when block is empty and what is sent is only a backspace
        ## things might break down if any stroke translation has "\n" in the middle of text, ie "previous\nnew"
        if len(focus_block.text()) == 0 and not string_sent and backspaces_sent > 0:
            focus_block = focus_block.previous()
            # if this is first block, nothing happens
            if not focus_block:
                return
        ## return if nothing is sent or any backspaces, this might be a plover command, something like KPA, or others
        if not string_sent and backspaces_sent == 0:
            return
        block_dict = focus_block.userData()
        # if preexisting data, else initialize block data object
        if block_dict:
            block_dict = update_user_data(block_dict, key = "edittime")
        else:
            block_dict = BlockUserData()
        if not block_dict["creationtime"]:
            block_dict = update_user_data(block_dict, key = "creationtime")
        if block_dict["strokes"]:
            strokes_data = block_dict["strokes"]
        else:
            strokes_data = []
        if not block_dict["audiostarttime"]:
            if self.player.state() == QMediaPlayer.PlayingState:
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = audio_time)
            if self.recorder.state() == QMediaRecorder.RecordingState:
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = audio_time)
        if "\n" in string_sent and not current_cursor.atEnd():
            log.info("New line in translation + not end of document. Insert steno rather than append.")
            hold_cutcopy = self.cutcopy_storage
            list_segments = string_sent.splitlines(True)
            for i, segment in enumerate(list_segments):
                # because this is all occurring in one stroke, only first segment gets the stroke
                if i == 0:
                    stroke = [datetime.now().isoformat("T", "milliseconds"), raw_steno, segment]
                else:
                    stroke = [datetime.now().isoformat("T", "milliseconds"), "", segment]
                dummy_action_dict = {"action": "steno", "block": self.cursor_block, "position_in_block": current_cursor.positionInBlock(),
                            "text": segment.rstrip("\n"), "length": len(string_sent), "steno": stroke}
                self.cutcopy_storage = dummy_action_dict
                self.paste_steno()
                current_cursor.insertText("\n")
            self.cutcopy_storage = hold_cutcopy
            self.last_string_sent = ""
            return
        if string_sent and not current_cursor.atEnd():
            log.info("Cursor in middle. Insert steno rather than append.")
            hold_cutcopy = self.cutcopy_storage
            stroke = [datetime.now().isoformat("T", "milliseconds"), raw_steno, string_sent]
            dummy_action_dict = {"action": "steno", "block": self.cursor_block, "position_in_block": current_cursor.positionInBlock(),
                            "text": string_sent, "length": len(string_sent), "steno": stroke}
            self.cutcopy_storage = dummy_action_dict
            self.paste_steno()
            self.cutcopy_storage = hold_cutcopy
            self.last_string_sent = ""
            return
        if backspaces_sent != 0 and not current_cursor.atEnd():
            hold_cutcopy = self.cutcopy_storage
            log.info("Cursor in middle. Extract steno rather than remove from end.")
            cursor_pos = current_cursor.positionInBlock()
            remaining_text_len = len(focus_block.text()) - cursor_pos
            holding_space = backspaces_sent
            if holding_space > cursor_pos:
                initial_block = current_cursor.blockNumber()
                initial_block_pos = cursor_pos
                if holding_space > current_cursor.position():
                    final_block = 0
                    final_block_pos = 0
                else:
                    current_cursor.setPosition(current_cursor.position() - holding_space)
                    final_block = current_cursor.blockNumber()
                    final_block_pos = current_cursor.positionInBlock()
                coords = [0] * (initial_block-final_block) + [final_block_pos]
                current_cursor.setPosition(self.textEdit.document().findBlockByNumber(initial_block).position() + initial_block_pos)
                for seg, coords in zip(list(range(initial_block, final_block-1, -1)), coords):
                    self.textEdit.setTextCursor(current_cursor)
                    if coords == 0:
                        current_cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
                        self.textEdit.setTextCursor(current_cursor)
                        self.cut_steno()
                        self.merge_paragraphs(add_space = False)
                        current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor, remaining_text_len)
                    else:
                        current_cursor.setPosition(self.textEdit.document().findBlockByNumber(seg).position() + final_block_pos, QTextCursor.KeepAnchor)
                        self.textEdit.setTextCursor(current_cursor)
                        self.cut_steno()
                self.cutcopy_storage = hold_cutcopy
                self.last_backspaces_sent = 0
                return
            current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, backspaces_sent)
            self.textEdit.setTextCursor(current_cursor)
            self.cut_steno()
            self.cutcopy_storage = hold_cutcopy
            self.last_backspaces_sent = 0
            return
        if backspaces_sent != 0:
            strokes_data = remove_strings(strokes_data, backspaces_sent)
        if string_sent:
            stroke = [datetime.now().isoformat("T", "milliseconds"), raw_steno, string_sent]
            if self.player.state() == QMediaPlayer.PlayingState: stroke.append(real_time)
            if self.recorder.state() == QMediaRecorder.RecordingState: stroke.append(real_time)
            if type(strokes_data) is str:
                strokes_data = []
            strokes_data.append(stroke)
        block_dict = update_user_data(block_dict, key = "strokes", value = strokes_data) 
        focus_block.setUserData(block_dict)
        # mimic keyboard actions
        if backspaces_sent != 0:
            stroke = [datetime.now().isoformat("T", "milliseconds"), raw_steno, ""]
            # select backward the number of backspaces
            current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, backspaces_sent)
            deleted_text = current_cursor.selectedText()
            current_cursor.removeSelectedText()
            action_dict = {"action": "backspace", "block": self.cursor_block, "position_in_block": current_cursor.positionInBlock(),
                            "text": deleted_text, "length": len(deleted_text), "steno": stroke}
            self.last_backspaces_sent = 0
        if string_sent:
            action_dict = {"action": "steno", "block": self.cursor_block, "position_in_block": current_cursor.positionInBlock(),
                            "text": string_sent, "length": len(string_sent), "steno": stroke}
            current_cursor.insertText(string_sent)       
            self.last_string_sent = ""
        self.last_action.append(action_dict)
        self.textEdit.document().setModified(True)
        self.statusBar.clearMessage()

    def copy_steno(self, store = True):
        log.info("Performing copying.")
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            log.info("No text selected for copying, skipping")
            self.statusBar.showMessage("Select text for copying")
            return
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        stop_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        selected_text = current_cursor.selectedText()
        if re.search("\u2029", selected_text):
            # maybe one day in the far future
            self.statusBar.showMessage("Copying across paragraphs is not supported")
            return
        block_data = current_block.userData()
        log.debug(block_data.return_all())
        copy_steno = extract_stroke_data(block_data["strokes"], start_pos, stop_pos, copy = True)
        action_dict = {"action": "copy", "block": current_block_num, "position_in_block": start_pos, "text": selected_text,
                        "length": len(selected_text), "steno": copy_steno}
        self.textEdit.moveCursor(QTextCursor.End)
        log.info("Copy: %s" % str(action_dict))
        if store:
            self.cutcopy_storage = action_dict
            log.info("Copy: action stored for pasting")
            # self.last_action = action_dict
            self.statusBar.showMessage("Copied from paragraph {par_num}, from {start} to {end}".format(par_num = current_block_num, start = start_pos, end = stop_pos))

    def cut_steno(self, store = True):
        log.info("Perform cutting.")
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            log.info("No text selected, skipping")
            self.statusBar.showMessage("Select text for cutting")
            return
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        stop_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        log.info("Cut: Cut in paragraph %s from %s to %s" % (current_block_num, start_pos, stop_pos))
        selected_text = current_cursor.selectedText()
        if re.search("\u2029", selected_text):
            # maybe one day in the far future
            self.statusBar.showMessage("Cutting across paragraphs is not supported")
            return
        block_data = current_block.userData()
        log.debug(block_data.return_all())
        remainder, cut_steno = extract_stroke_data(block_data["strokes"], start_pos, stop_pos, copy = False)
        current_cursor.removeSelectedText()
        block_data = update_user_data(block_data, key = "strokes", value = remainder)
        block_data = update_user_data(block_data, "edittime")
        current_block.setUserData(block_data)             
        action_dict = {"action": "cut", "block": current_block_num, "position_in_block": start_pos, "text": selected_text,
                        "length": len(selected_text), "steno": cut_steno}
        log.info("Cut: %s" % str(action_dict))
        # store both as an action, and for pasting
        if store:
            self.cutcopy_storage = action_dict
            log.info("Cut: action stored for pasting")
            self.last_action.append(action_dict)
            log.info("Cut: action appended to history, %s long" % len(self.last_action))
            self.statusBar.showMessage("Cut from paragraph {par_num}, from {start} to {end}".format(par_num = current_block_num, start = start_pos, end = stop_pos))

    def paste_steno(self, store = True):
        log.info("Performing pasting.")
        action_dict = deepcopy(self.cutcopy_storage)
        if action_dict == "":
            log.info("Nothing in storage to paste, skipping")
            self.statusBar.showMessage("Cut or copy text to paste")
            return
        current_cursor = self.textEdit.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        log.info("Paste: Pasting in paragraph %s at position %s" % (current_block_num, start_pos))
        block_data = current_block.userData()
        log.debug(block_data.return_all())
        before, after = split_stroke_data(block_data["strokes"], start_pos)
        log.debug("Paste: Splitting pieces %s and %s with %s" % (before, after, action_dict["steno"]))
        steno = action_dict["steno"]
        if before and after:
            before = before + steno
            before = before + after
            new_stroke_data = before
        elif before and not after:
            new_stroke_data = before + steno
        elif not before and after:
            new_stroke_data = steno + after
        else:
            new_stroke_data = steno
        log.info("Paste: Insert text at %s" % str(current_block.position() + start_pos))
        current_cursor.setPosition(current_block.position() + start_pos, QTextCursor.MoveAnchor)
        current_cursor.insertText(action_dict["text"])
        block_data = update_user_data(block_data, key = "strokes", value = new_stroke_data)
        block_data = update_user_data(block_data, "edittime")
        log.debug("After paste: %s", block_data.return_all())
        current_block.setUserData(block_data)
        action_dict["action"] = "paste"
        action_dict["block"] = current_block_num
        action_dict["position_in_block"] = start_pos
        # self.textEdit.moveCursor(QTextCursor.End)
        if store:
            self.last_action.append(action_dict)
            log.info("Paste: action appended to history, %s long" % len(self.last_action))
            self.statusBar.showMessage("Paste to paragraph {par_num}, at position {start}".format(par_num = current_block_num, start = start_pos))       

    def split_paragraph(self, store = True):
        log.info("Start splitting operation.")
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            self.statusBar.showMessage("Indicate split location by selecting text")
            return
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        split_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        log.info("Splitting at position " + split_pos + " in block " + current_block_num)
        block_data = current_block.userData()
        block_text = current_block.text()
        stroke_data = block_data["strokes"]
        first_part, second_part = split_stroke_data(stroke_data, split_pos)
        first_text = block_text[:split_pos]
        second_text = block_text[split_pos:]
        if self.config["space_placement"] == "Before Output":
            if second_part[0][2].startswith(" "):
                log.info("Stripping space from beginning of second piece")
                second_part[0][2] = second_part[0][2].lstrip(" ")
                second_text = second_text.lstrip(" ")
        log.info("Split: Appending new line stroke to end of second piece")
        fake_newline_stroke = [datetime.now().isoformat("T", "milliseconds"), "R-R", "\n"]
        first_part.append(fake_newline_stroke)
        first_data = current_block.userData()
        second_data = BlockUserData()
        second_data = update_user_data(second_data, key = "strokes", value = second_part)
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
        second_data = update_user_data(second_data, key = "creationtime", value = second_part[0][0])
        second_data = update_user_data(second_data, key = "edittime")
        first_data = update_user_data(first_data, key = "strokes", value = first_part)
        first_data = update_user_data(first_data, key = "edittime")
        current_cursor.setPosition(min(current_cursor.position(), current_cursor.anchor()))
        log.info("Split: Set cursor position to " + min(current_cursor.position(), current_cursor.anchor()))
        current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        log.info("Split: Move cursor position to end of block")
        current_cursor.removeSelectedText()
        log.info("Split: Removing selected text")
        current_cursor.insertBlock()
        log.info("Split: Insert new block")
        current_cursor.insertText(second_text)
        log.info("Split: Insert new text " + second_text)
        new_block = current_block.next()
        current_block.setUserData(first_data)
        new_block.setUserData(second_data)
        self.textEdit.moveCursor(QTextCursor.End)
        action_dict = {"action": "split", "block": current_block_num, "position_in_block": 0, "text": first_text, "length": split_pos, "steno": first_part}
        log.info("Split: %s" % str(action_dict))
        if store:
            self.cutcopy_storage = action_dict
            log.info("Split: action stored for pasting")
            self.last_action.append(action_dict)
            log.info("Split: action appended to history, %s long" % len(self.last_action))
            self.statusBar.showMessage("Split paragraph {par_num} at position {split_pos}".format(par_num = current_block_num, split_pos = split_pos))

    def merge_paragraphs(self, store = True, add_space = True):
        log.info("Performing merging")
        current_cursor = self.textEdit.textCursor()
        second_block_num = current_cursor.blockNumber()
        if second_block_num == 0:
            log.info("Merge: This is first paragraph, skipping merging.")
            self.statusBar.showMessage("Select second of the paragraphs wanted for merge")
            return
        first_block_num = second_block_num - 1
        log.info("Merge: Merging paragraphs %s and %s" % (first_block_num, second_block_num))
        first_block = self.textEdit.document().findBlockByNumber(first_block_num)
        second_block = self.textEdit.document().findBlockByNumber(second_block_num)
        first_data = first_block.userData()
        second_data = second_block.userData()
        # for style, first trumps second, same for creation time of block
        # edit time is new
        first_data = update_user_data(first_data, key = "edittime")
        # append second stroke data to first
        second_strokes = second_data["strokes"]
        first_strokes = first_data["strokes"]
        # remove the new line from the stroke data
        if first_strokes[-1][2] == "\n":
            log.info("Merge: Removing new line from first paragraph steno, replacing with space")
            del first_strokes[-1]
            # if the newline is removed, a space should be added somewhere
            # this depends on whether spaces are added before or after
        if self.config["space_placement"] == "Before Output" and add_space:
            second_strokes[0][2] = " " + second_strokes[0][2]
        elif add_space:
            first_strokes[-1][2] = first_strokes[-1][2] + " "
        first_text = first_block.text()
        if add_space:
            new_block_text = " " + second_block.text()
        else:
            new_block_text = second_block.text()
        new_strokes = first_strokes + second_strokes
        first_data = update_user_data(first_data, key = "strokes", value = new_strokes)
        # update the audio end time if it exists, only really needed for last block since other blocks do not have audioendtime
        if first_data["audioendtime"] != second_data["audioendtime"]:
            first_data = update_user_data(first_data, key = "audioendtime", value = second_data["audioendtime"])
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()
        log.info("Merge: Deleting second paragraph")
        first_block.setUserData(first_data)
        current_cursor.insertText(new_block_text)
        log.info("Merge: Inserting text %s into paragraph" % new_block_text)
        # since second block is "destroyed", the action block uses first block data, tracking end of first block text in length
        action_dict = {"action": "merge", "block": first_block_num, "position_in_block": 0, "text": first_text, "length": len(first_text), "steno": first_strokes}
        log.info("Merge: %s" % str(action_dict))
        if store:
            self.cutcopy_storage = action_dict
            log.info("Merge: action stored for pasting")
            self.last_action.append(action_dict)
            log.info("Merge: action appended to history, %s long" % len(self.last_action))
            self.statusBar.showMessage("Merge paragraphs {par_one} and {par_two}".format(par_one = first_block_num, par_two = second_block_num))  

    def undo_action(self):
        current_cursor = self.textEdit.textCursor()
        if len(self.last_action) == 0:
            self.statusBar.showMessage("No action in history to undo.")
            return
        action_dict = self.last_action.pop()
        log.info("Undo: Undoing %s" % action_dict)
        if action_dict["action"] in ["steno", "paste"]:
            start_pos = action_dict["position_in_block"]
            end_pos = action_dict["length"]
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"])
            current_cursor.setPosition(focus_block.position())
            current_cursor.setPosition(focus_block.position() + start_pos)
            current_cursor.setPosition(focus_block.position() + start_pos + end_pos, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            log.info("Undo: Undo with a cut.")
            self.cut_steno(store = False)
        elif action_dict["action"] in ["backspace", "cut"]:
            start_pos = action_dict["position_in_block"]
            end_pos = action_dict["length"]
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"])
            current_cursor.setPosition(focus_block.position() + start_pos)
            self.textEdit.setTextCursor(current_cursor)
            hold_old_storage = self.cutcopy_storage
            log.debug("Undo: Store away clipboard data. %s", hold_old_storage)
            self.cutcopy_storage = action_dict
            log.debug("Undo: Put action into clipboard storage for undo, %s", self.cutcopy_storage)            
            log.info("Undo: Undo with a paste.")
            self.paste_steno(store = False)
            self.cutcopy_storage = hold_old_storage
            log.debug("Undo: Restore old clipboard data.")    
        elif action_dict["action"] == "merge":
            start_pos = action_dict["length"]
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"])
            current_cursor.setPosition(focus_block.position() + start_pos)
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            log.info("Undo: Undo with split paragraph.")
            self.split_paragraph(store = False)
        elif action_dict["action"] == "split":
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"] + 1)
            current_cursor.setPosition(focus_block.position())
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            log.info("Undo: Undo with merge paragraph")
            self.merge_paragraphs(store = False)            
        else:
            log.info("Unknown action. Not undoing anything.")
            return
        self.redone_action.append(action_dict)
        log.info("Undo length: %s, Redo length: %s" % (len(self.last_action), len(self.redone_action)))

    def redo_action(self):
        current_cursor = self.textEdit.textCursor()
        if len(self.redone_action) == 0:
            self.statusBar.showMessage("No action in undo history to redo.")
            return
        action_dict = self.redone_action.pop()
        log.info("Redo: Redoing %s" % action_dict)
        if action_dict["action"] in ["steno", "paste"]:
            start_pos = action_dict["position_in_block"]
            end_pos = action_dict["length"]
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"])
            current_cursor.setPosition(focus_block.position() + start_pos)
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            hold_old_storage = self.cutcopy_storage
            log.debug("Redo: Store away clipboard data. %s", hold_old_storage)
            self.cutcopy_storage = action_dict
            log.debug("Redo: Put action into clipboard storage for redo, %s", self.cutcopy_storage)
            log.info("Redo: Redo with a paste.")
            self.paste_steno(store = False)
            log.debug("Redo: Restore old clipboard data.")
            self.cutcopy_storage = hold_old_storage
        elif action_dict["action"] in ["backspace", "cut"]:
            start_pos = action_dict["position_in_block"]
            end_pos = action_dict["length"]
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"])
            current_cursor.setPosition(focus_block.position())
            current_cursor.setPosition(focus_block.position() + start_pos)
            current_cursor.setPosition(focus_block.position() + start_pos + end_pos, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            log.info("Redo: Redo with a cut.")
            self.cut_steno(store = False)
        elif action_dict["action"] == "merge":
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"] + 1)
            current_cursor.setPosition(focus_block.position())
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            log.info("Redo: Redo with merge paragraphs.")
            self.merge_paragraphs(store = False)
        elif action_dict["action"] == "split":
            start_pos = action_dict["length"]
            focus_block = self.textEdit.document().findBlockByNumber(action_dict["block"])
            current_cursor.setPosition(focus_block.position() + start_pos)
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.textEdit.setTextCursor(current_cursor)
            log.info("Undo: Undo with split paragraph.")
            self.split_paragraph(store = False)
        else:
            log.info("Unknown action. Not redoing.")
            return
        self.last_action.append(action_dict)
        log.info("Undo length: %s, Redo length: %s" % (len(self.last_action), len(self.redone_action)))
    # search functions
    def show_find_replace(self):
        if self.textEdit.textCursor().hasSelection() and self.search_text.isChecked():
            self.search_term.setText(self.textEdit.textCursor().selectedText())
        self.toolBox.setCurrentWidget(self.find_replace_pane)

    def search(self, direction = 1):
        if self.search_untrans.isChecked():
            search_status = self.untrans_search(direction)
        elif self.search_steno.isChecked():
            search_status = self.steno_wrapped_search(direction)
        else:
            search_status = self.text_search(direction)
        return(search_status)

    def text_search(self, direction = 1):
        flags = QTextDocument.FindFlags()
        search = self.search_term.text()
        if self.search_case.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        if self.search_whole.isChecked():
            flags |= QTextDocument.FindWholeWords
        if direction == -1:
            flags |= QTextDocument.FindBackward
        cursor = self.textEdit.textCursor()
        log.info("Performing text search with term %s, flags %s.", search, flags)
        found = self.textEdit.document().find(search, cursor, flags)
        if not found.isNull():
            log.info("Search success.")
            self.textEdit.setTextCursor(found)
            self.statusBar.showMessage("Match found")
            return True
        elif self.search_wrap.isChecked():
            log.info("Search failure. Wrapping.")
            if direction == 1:
                cursor.movePosition(QTextCursor.Start)
            else:
                cursor.movePosition(QTextCursor.End)
            found = self.textEdit.document().find(search, cursor, flags)
            if not found.isNull():
                log.info("Search success.")
                self.textEdit.setTextCursor(found)
                self.statusBar.showMessage("Wrapped search. Match found.")
                return True
            else:
                log.info("Search failure.")
                self.statusBar.showMessage("Wrapped search. No match found.")
                return None
        else:
            log.info("Search failure.")
            self.statusBar.showMessage("No match found.")
            return None

    def steno_wrapped_search(self, direction = 1):
        log.info("Steno search.")
        found = self.steno_search(direction = direction)
        if not found and self.search_wrap.isChecked():
            log.info("Wrap steno search.")
            cursor = self.textEdit.textCursor()
            if direction == -1:
                log.info("Search starting from end.")
                cursor.movePosition(QTextCursor.End)
            else:
                log.info("Search starting from top.")
                cursor.movePosition(QTextCursor.Start)
            self.textEdit.setTextCursor(cursor)
            found = self.steno_search(direction = direction)
        return(found)

    def steno_search(self, direction = 1):
        cursor = self.textEdit.textCursor()
        steno = self.search_term.text()
        log.info("Searching for stroke %s in stroke data.", steno)
        if direction == -1:
            current_block = cursor.block()
            if cursor.hasSelection():
                start_pos = min(cursor.position(), cursor.anchor())
                cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor)
            self.textEdit.setTextCursor(cursor)
            cursor_pos = cursor.positionInBlock()
            current_stroke_data = current_block.userData()["strokes"]
            stroke_data, second_part = split_stroke_data(current_stroke_data, cursor_pos)
            while True:
                check_match = [stroke[1] == steno for stroke in stroke_data]
                if any(check_match):
                    break
                if current_block == self.textEdit.document().firstBlock():
                    # end search after searching last block
                    stroke_data = None
                    break
                current_block = current_block.previous()
                stroke_data = current_block.userData()["strokes"] 
            if stroke_data is not None:
                match_index = [i for i, x in enumerate(check_match) if x][-1]
                block_pos = current_block.position()
                current_stroke_data = current_block.userData()["strokes"]
                start_pos = block_pos + sum([len(stroke[2]) for stroke in current_stroke_data[:match_index]])
                end_pos = start_pos + len(current_stroke_data[match_index][2])
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(cursor)
                log.info("Search success.")
                self.statusBar.showMessage("Steno match found.")
                return True
            else:
                log.info("Search failure.")
                self.statusBar.showMessage("No steno match found.")
                return None                                                                            
        else:
            current_block = cursor.block()
            if cursor.hasSelection():
                start_pos = max(cursor.position(), cursor.anchor())
                cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor)
            self.textEdit.setTextCursor(cursor)
            cursor_pos = cursor.positionInBlock()
            current_stroke_data = current_block.userData()["strokes"]
            first_part, stroke_data = split_stroke_data(current_stroke_data, cursor_pos)
            while True:
                check_match = [stroke[1] == steno for stroke in stroke_data]
                if any(check_match):
                    break
                if current_block == self.textEdit.document().lastBlock():
                    # end search after searching last block
                    stroke_data = None
                    break
                current_block = current_block.next()
                # if moving away from starting block, first part doesn't matter
                first_part = None
                stroke_data = current_block.userData()["strokes"]
            if stroke_data is not None:
                match_index = [i for i, x in enumerate(check_match) if x][0]
                if first_part:
                    match_index = len(first_part) - 1 + match_index
                block_pos = current_block.position()
                current_stroke_data = current_block.userData()["strokes"]
                start_pos = block_pos + sum([len(stroke[2]) for stroke in current_stroke_data[:match_index]])
                end_pos = start_pos + len(current_stroke_data[match_index][2])
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(cursor)
                log.info("Search success.")
                self.statusBar.showMessage("Steno match found.")
                return True
            else:
                log.info("Search failure.")
                self.statusBar.showMessage("No steno match found.")
                return None

    def untrans_search(self, direction = 1):
        flags = QTextDocument.FindFlags()
        untrans_reg = QRegExp("(\\b|\\*)(?=[STKPWHRAO*EUFBLGDZ]{3,})S?T?K?P?W?H?R?A?O?\*?E?U?F?R?P?B?L?G?T?S?D?Z?\\b")
        if direction == -1:
            flags |= QTextDocument.FindBackward
        cursor = self.textEdit.textCursor()
        found = self.textEdit.document().find(untrans_reg, cursor, flags)
        log.info("Search for untranslated steno.")
        if not found.isNull():
            self.textEdit.setTextCursor(found)
            log.info("Search success.")
            self.statusBar.showMessage("Untrans found") 
            return True
        elif self.search_wrap.isChecked():
            if direction == 1:
                cursor.movePosition(QTextCursor.Start)
            else:
                cursor.movePosition(QTextCursor.End)
            found = self.textEdit.document().find(untrans_reg, cursor, flags)
            if not found.isNull():
                self.textEdit.setTextCursor(found)
                log.info("Wrapped. Search success.")
                self.statusBar.showMessage("Wrapped search. Untrans found.")
                return True
            else:
                log.info("Wrapped. Search failure.")
                self.statusBar.showMessage("Wrapped search. No untrans found.")
                return None
        else:
            self.statusBar.showMessage("No untrans found.") 
            return None      

    def search_text_options(self):
        if self.search_text.isChecked():
            self.search_case.setEnabled(True)
            self.search_whole.setChecked(False)
            self.search_term.setEnabled(True)
            self.search_whole.setEnabled(True)

    def search_steno_options(self):
        if self.search_steno.isChecked():
            self.search_case.setEnabled(False)
            self.search_whole.setChecked(True)
            self.search_term.setEnabled(True)
            self.search_whole.setEnabled(True)

    def search_untrans_options(self):
        if self.search_untrans.isChecked():
            self.search_term.setEnabled(False)
            self.search_case.setEnabled(False)
            self.search_whole.setChecked(False)
            self.search_whole.setEnabled(False)           

    def replace(self, to_next = True):
        log.info("Perform replacement.")
        if self.textEdit.textCursor().hasSelection():
            log.info("Replace: Replace %s with %s", self.textEdit.textCursor().selectedText(), self.replace_term.text())
            self.cut_steno(store = True)
            log.debug("Replace: modifying action dict from cut operation to paste operation.")
            action_dict = deepcopy(self.cutcopy_storage)
            action_dict["text"] = self.replace_term.text()
            strokes = action_dict["steno"]
            strokes[0][2] = self.replace_term.text()
            if len(strokes) > 1:
                for i in range(1,len(strokes)):
                    strokes[i][2] = ""
            action_dict["steno"] = strokes
            action_dict["length"] = len(self.replace_term.text())
            log.debug("Replace: modified action dict %s", action_dict)
            self.cutcopy_storage = action_dict
            self.paste_steno(store = True)
        if to_next:
            log.info("Moving to next match.")        
            if self.search_untrans.isChecked():
                search_status = self.untrans_search()
            elif self.search_steno.isChecked():
                search_status = self.steno_wrapped_search()
            else:
                search_status = self.text_search()
            return(search_status)

    def replace_everything(self):
        cursor = self.textEdit.textCursor()
        old_wrap_state = self.search_wrap.isChecked()
        if old_wrap_state:
            self.search_wrap.setChecked(False)
        old_cursor_position = cursor.block().position()        
        cursor.movePosition(QTextCursor.Start)
        self.textEdit.setTextCursor(cursor)
        search_status = True
        log.info("Replace all: starting from beginning.")
        while search_status:
            search_status = self.search()
            if search_status is None:
                break
            self.replace(to_next = False)
        # not the exact position but hopefully close
        log.info("Replace all: attempting to set cursor back to original positio.")
        cursor.setPosition(old_cursor_position)
        self.textEdit.setTextCursor(cursor)
        self.search_wrap.setChecked(old_wrap_state)
    # audio functions
    def open_audio(self):
        if not self.file_name:
            log.info("No audio file selected, skipping")
            return
        audio_file = QFileDialog.getOpenFileName(self, _("Select Audio/Video File"), str(self.file_name), "Audio/Video Files (*.mp3 *.ogg *.wav *.mp4 *.mov *.wmv *.avi)")
        if audio_file[0]:
            self.audio_file = pathlib.Path(audio_file[0])
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(self.audio_file))))
            log.info("Player set to selected audio " + str(audio_file[0]))
            label_text = "Audio:" + str(self.audio_file.name)
            self.audio_label.setText(label_text)
            self.statusBar.showMessage("Opened audio file {filename}".format(filename = str(audio_file[0])))

    def show_hide_video(self):
        if self.viewer.isVisible():
            self.viewer.hide()
        else:
            self.viewer.show()

    def set_up_video(self, avail):
        if avail:
            log.info("Video available for file.")
            self.viewer = QMainWindow()
            self.video = QVideoWidget()
            self.player.setVideoOutput(self.video)
            self.viewer.setWindowFlags(self.viewer.windowFlags() | Qt.WindowStaysOnTopHint)
            self.viewer.setCentralWidget(self.video)
            log.info("Showing video widget.")
            self.video.updateGeometry()
            self.video.adjustSize()
            self.viewer.show()
        else:
            # self.viewer.hide()
            pass

    def play_pause(self):
        log.info("User press playing/pausing audio.")
        if self.recorder.state() == QMediaRecorder.StoppedState:
            pass
        else:
            log.info("Recording ongoing, passing.")
            self.statusBar.showMessage("Recording in progress.")
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            log.info("Paused audio.")
            self.statusBar.showMessage("Paused audio")
        else:
            self.player.play()
            block_dict = self.textEdit.document().findBlockByNumber(self.cursor_block).userData()
            if not block_dict:
                block_dict = BlockUserData()
                block_dict = update_user_data(block_dict, "creationtime")
            if not block_dict["audiostarttime"]:
                real_time = self.player.position() - self.audioDelay.value()
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = ms_to_hours(real_time))
            log.debug("Adding audio timestamp to data, %s", block_dict.return_all())
            self.textEdit.document().findBlockByNumber(self.cursor_block).setUserData(block_dict)
            log.info("Playing audio.")
            self.statusBar.showMessage("Restarted audio")
            
    def stop_play(self):
        log.info("User press stop audio.")
        block_dict = self.textEdit.document().findBlockByNumber(self.cursor_block).userData()
        real_time = self.player.position() - self.audioDelay.value()
        block_dict = update_user_data(block_dict, key = "audioendtime", value = ms_to_hours(real_time))
        log.debug("Adding audio timestamp to data, %s", block_dict.return_all())
        self.textEdit.document().findBlockByNumber(self.cursor_block).setUserData(block_dict)
        self.player.stop()
        log.info("Audio stopped.")
        self.statusBar.showMessage("Stopped audio")

    def update_duration(self, duration):
        self.audio_seeker.setMaximum(duration)
        self.audio_duration.setText(ms_to_hours(duration))

    def update_seeker_track(self, position):
        self.audio_seeker.setValue(position)
        self.audio_curr_pos.setText(ms_to_hours(position))

    def set_position(self, position):
        self.player.setPosition(position)
        log.info("User set audio track to %s", ms_to_hours(position))

    def seek_position(self, direction = 1):
        log.info("User skip ahead/behind audio.")
        seek_time = self.player.position() + direction * 5000
        self.player.setPosition(seek_time)

    def update_playback_rate(self, rate):
        log.info("User set audio playback rate.")
        self.player.setPlaybackRate(rate)

    def record_controls_enable(self, value = True):
        self.actionStop_Recording.setEnabled(not value)
        self.audio_device.setEnabled(value)
        self.audio_codec.setEnabled(value)
        self.audio_container.setEnabled(value)
        self.audio_sample_rate.setEnabled(value)
        self.audio_channels.setEnabled(value)
        self.constant_quality.setEnabled(value)
        self.quality_slider.setEnabled(value)
        self.constant_bitrate.setEnabled(value)
        self.audio_bitrate.setEnabled(value)

    def recorder_error(self):
        self.statusBar.setMessage(self.recorder.errorString())

    def record_or_pause(self):
        if self.player.state() != QMediaPlayer.StoppedState:
            log.info("Audio playing, passing.")
            self.statusBar.showMessage("Playing in progress.")
            return
        else:
            pass
        self.record_controls_enable(False)
        if self.recorder.state() == QMediaRecorder.StoppedState:
            settings = QAudioEncoderSettings()
            audio_input = self.audio_device.itemText(self.audio_device.currentIndex())
            audio_codec = self.audio_device.itemText(self.audio_codec.currentIndex())
            audio_container = self.audio_container.itemText(self.audio_container.currentIndex())
            audio_sample_rate = int(self.audio_sample_rate.itemText(self.audio_sample_rate.currentIndex()))
            audio_channels = self.audio_channels.itemData(self.audio_channels.currentIndex())
            audio_bitrate = self.audio_bitrate.itemData(self.audio_bitrate.currentIndex())
            audio_encoding = QMultimedia.ConstantQualityEncoding if self.constant_quality.isChecked() else QMultimedia.ConstantBitRateEncoding
            self.recorder.setAudioInput(audio_input)
            settings.setCodec(audio_codec)
            settings.setSampleRate(audio_sample_rate)
            settings.setBitRate(audio_bitrate)
            settings.setChannelCount(audio_channels)
            settings.setQuality(QMultimedia.EncodingQuality(self.quality_slider.value()))
            settings.setEncodingMode(audio_encoding)
            log.info("Audio settings:\nAudio Input: %s\nCodec: %s\nMIME Type: %s\nSample Rate: %s\nChannels: %s\nQuality: %s\nBitrate: %s\nEncoding:%s",
                        audio_input, audio_codec, audio_container, audio_sample_rate, audio_channels, str(QMultimedia.EncodingQuality(self.quality_slider.value())), audio_bitrate, audio_encoding)
            self.recorder.setEncodingSettings(settings, QVideoEncoderSettings(), audio_container)
            common_file_formats = ["aac", "amr", "flac", "gsm", "m4a", "mp3", "mpc", "ogg", "opus", "raw", "wav"]
            guessed_format = [ext for ext in common_file_formats if ext in audio_container]
            if len(guessed_format) == 0:
                audio_file_path = self.file_name / "audio" / self.file_name.stem
            else:
                audio_file_path = self.file_name / "audio" / (self.file_name.stem + "." + guessed_format[0])
            try:
                os.mkdir(self.file_name / "audio")
            except FileExistsError:
                pass
            if audio_file_path.exists():
                user_choice = QMessageBox.question(self, "Record", "Are you sure you want to replace existing audio?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if user_choice == QMessageBox.Yes:
                    log.info("User choice to record over existing audio file.")
                    pass
                else:
                    log.info("Abort recording attempt.")
                    return
            self.recorder.setOutputLocation(QUrl.fromLocalFile(str(audio_file_path)))
            log.info("Recording to %s", str(audio_file_path))
            self.statusBar.showMessage("Recording audio at {filename}".format(filename = str(audio_file_path)))
            self.recorder.record()
        else:
            log.info("Pausing recording.")
            self.statusBar.showMessage("Pausing recording.")
            self.recorder.pause()
    
    def stop_record(self):
        self.recorder.stop()
        log.info("Stop recording.")
        self.record_controls_enable(True)

    def update_record_time(self):
        msg = "Recorded %s" % ms_to_hours(self.recorder.duration())
        self.statusBar.showMessage(msg)
    # export functions
    def export_text(self):
        selected_folder = pathlib.Path(self.file_name)
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(selected_folder.stem).with_suffix(".txt"))
            , _("Transcript (*.txt)")
        )
        if not selected_file[0]:
            return
        contents = self.textEdit.document().toRawText()
        file_path = pathlib.Path(selected_file[0])
        log.info("Exporting plain text to %s.", str(file_path))
        with open(file_path, "w") as f:
            f.write(contents)
            self.statusBar.showMessage("Exported to {filename} in plain text format".format(filename = str(file_path)))

    def export_ascii(self):
        selected_folder = pathlib.Path(self.file_name)
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(selected_folder.stem).with_suffix(".txt"))
            , _("Transcript (*.txt)")
        )
        if not selected_file[0]:
            return
        contents = self.textEdit.document().toRawText()
        par_contents = contents.split("\n")
        wrapped_text = []
        for par in par_contents:
            wrapped_text += textwrap.wrap(par)
        page_number = 1
        max_lines = 25 # this could be adjustable
        doc_lines = []
        for i in range(0, len(wrapped_text), max_lines):
            doc_lines += [f'{page_number:04}']
            page_number +=1
            # padding space, column 2 is start of line number (left justified), column 7 is start of text
            # <space> number{1,2} [space]{3,4}
            doc_lines += [str(line_num).ljust(5).rjust(6) + text for line_num, text in zip(range(1, max_lines), wrapped_text[i: i + max_lines])]
        file_path = pathlib.Path(selected_file[0])
        log.info("Export ASCII to %s.", str(file_path))
        with open(file_path, "w") as f:
            for line in doc_lines:
                f.write(f"{line}\n")
            self.statusBar.showMessage("Exported to {filename} in ASCII format".format(filename = str(file_path)))

    def export_srt(self):
        """
        srt format: line 1: block number
                    line 2: timestamp from --> to (millisecond separator comma, not period)
                    line 3: text
                    line 4: empty
                    line 7: textstart
        """
        selected_folder = pathlib.Path(self.file_name)
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(selected_folder.stem).with_suffix(".srt"))
            , _("Captions (*.srt)")
        )
        if not selected_file[0]:
            return
        block_num = 1
        doc_lines = []
        log.info("Attempting to export srt caption file.")
        for i in range(self.textEdit.blockCount()):
            log.debug("Setting timestamps for par %d", i)
            current_block = self.textEdit.document().findBlockByNumber(i)
            block_data = current_block.userData()
            doc_lines += [str(block_num)]
            block_num += 1
            audiostarttime = block_data["audiostarttime"]
            # webvtt uses periods for ms separator
            audiostarttime = audiostarttime.replace(".", ",")
            if block_data["audioendtime"]:
                audioendtime = block_data["audioendtime"]
            elif current_block == self.textEdit.document().end():
                log.debug("Block %d does not have audioendtime. Last block in document. Setting 0 as timestamp.", i)
                audioendtime = ms_to_hours(0)
            else:
                log.debug("Block %d does not have audioendtime. Attempting to use starttime from next block.", i)
                try:
                    audioendtime = current_block.next().userData()["audiostarttime"]
                except TypeError:
                    audioendtime = ms_to_hours(0)
            audioendtime = audioendtime.replace(".", ",")
            doc_lines += [audiostarttime + " --> " + audioendtime]
            doc_lines += [current_block.text()]
            doc_lines += [""]
        file_path = pathlib.Path(selected_file[0])
        with open(file_path, "w") as f:
            for line in doc_lines:
                f.write(f"{line}\n")
            self.statusBar.showMessage("Exported to {filename} in srt format".format(filename = str(file_path)))
            log.info("srt file successfully exported to %s", str(file_path))
        
    def export_odt(self):
        selected_folder = pathlib.Path(self.file_name)
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(selected_folder.stem).with_suffix(".odt"))
            , _("OpenDocumentText (*.odt)")
        )
        if not selected_file[0]:
            return
        # automatically update config and save in case changes were not saved before
        self.update_config()
        set_styles = self.styles
        if self.styles_path.suffix == ".json":
            textdoc = OpenDocumentText()
            # set page layout
            automatic_styles = textdoc.automaticstyles
            page_layout = PageLayout(name = "Transcript")
            page_layout_dict = {"pagewidth": self.page_width.text(), "pageheight": self.page_height.text(), "printorientation": "portrait",
                                "margintop": self.page_top_margin.text(), "marginbottom": self.page_bottom_margin.text(), 
                                "marginleft": self.page_left_margin.text(), "marginright": self.page_right_margin.text(), "writingmode": "lr-tb"}
            page_layout.addElement(PageLayoutProperties(attributes=page_layout_dict))
            automatic_styles.addElement(page_layout) 
            master_style = textdoc.masterstyles
            master_page = MasterPage(name = "Standard", pagelayoutname = "Transcript")
            master_style.addElement(master_page) 
            # set paragraph styles
            s = textdoc.styles
            if self.enable_line_num.isChecked():
                line_style = Style(name = "Line_20_numbering", displayname = "Line Numbering", family = "text")
                s.addElement(line_style)
                lineconfig_style = LinenumberingConfiguration(stylename = "Line_20_numbering", restartonpage = "true", offset = "0.2in", 
                                                                numformat = "1", numberposition = "left", increment = "5")
                s.addElement(lineconfig_style)
            fonts = textdoc.fontfacedecls
            # go through every style, get all font declarations, set the fontfamily as fontname
            doc_fonts = []
            for k, v in set_styles.items():
                try:
                    doc_fonts.append(v["textproperties"]["fontfamily"])
                except:
                    log.info("Exporting ODT: cannot set font family for ", k)
                    self.statusBar.showMessage("Cannot set font for style {style}".format(style = k))
            # here, the fontfamily gets single quotes because it won't work when font string has spaces
            # default font is set as modern, with fixed pitch
            for style_font in doc_fonts:
                fonts.addElement(FontFace(attributes={"name": style_font, "fontfamily": "'" + style_font + "'", "fontfamilygeneric": "modern", "fontpitch": "fixed"}))
            # loop through every element of style json, use try-except to still get through to odf even if some attributes are not correct
            for name, style in set_styles.items():
                style_name = name
                new_style = Style(name = style_name, family = "paragraph")
                if "parentstylename" in style:
                    new_style.setAttribute("parentstylename", style["parentstylename"])
                if "nextstylename" in style:
                    new_style.setAttribute("nextstylename", style["nextstylename"])      
                if "textproperties" in style:
                    text_prop = TextProperties()
                    for attribute, value in style["textproperties"].items():
                        # with loop, can try each attribute and skip if doesn't work
                        # better than stuffing all attributes in as a dict
                        try:
                            text_prop.setAttribute(attribute, value)
                        except:
                            pass
                    new_style.addElement(text_prop)
                if "paragraphproperties" in style:
                    par_prop = ParagraphProperties()
                    for attribute, value in style["paragraphproperties"].items():
                        try:
                            par_prop.setAttribute(attribute, value)
                        except:
                            pass
                    if "tabstop" in style["paragraphproperties"]:
                        style_tab = TabStops()
                        true_tab = TabStop(position = style["paragraphproperties"]["tabstop"])
                        style_tab.addElement(true_tab)
                        par_prop.addElement(style_tab)
                    new_style.addElement(par_prop)
                for attribute, value in style.items():
                    if attribute == "textproperties" or "paragraphproperties":
                        pass
                    try:
                        new_style.setAttribute(attribute, value)
                    except:
                        pass
                new_style.attributes
                s.addElement(new_style)
        else:
            textdoc = load(self.styles_path)
        for i in range(self.textEdit.blockCount()):
            block_data = self.textEdit.document().findBlockByNumber(i).userData()
            block_text = self.textEdit.document().findBlockByNumber(i).text()
            if not block_data["style"]:
                log.info("Paragraph %s has no style, setting to first style %s" % (i, next(iter(set_styles))))
                par_block = P(stylename = next(iter(set_styles)))
            else:
                par_block = P(stylename = block_data["style"])
            # this function is important to respect \t and other whitespace properly. 
            addTextToElement(par_block, block_text)
            textdoc.text.addElement(par_block)
        textdoc.save(selected_file[0])
        self.statusBar.showMessage("Exported to {filename} in OpenTextDocument format".format(filename = str(selected_file[0])))
        # os.startfile(selected_file[0])

    # import rtf
    def import_rtf(self):
        selected_folder = pathlib.Path(self.file_name)
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(selected_folder.stem).with_suffix(".rtf"))
            , _("RTF (*.rtf)")
        )
        if not selected_file[0]:
            return
        if not self.textEdit.document().isEmpty():
            user_choice = QMessageBox.question(self, "Import RTF", "Are you sure you want to import? This erases the present transcript.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.info("User choice to import and erase present document.")
                pass
            else:
                log.info("Abort import.")
                return
        parse_results = steno_rtf(selected_file[0])
        parse_results.parse_document()
        # for debug purposes
        file_path = pathlib.Path(pathlib.Path(selected_file[0]).name).with_suffix(".transcript")
        file_path = self.file_name / file_path
        with open(file_path, "w") as f:
            json.dump(parse_results.paragraphs, f)
        new_document = QTextDocument()
        new_document.setDocumentLayout(QPlainTextDocumentLayout(new_document))
        document_cursor = QTextCursor(new_document)
        self.statusBar.showMessage("Loading transcript data at from rtf {filename}".format(filename = str(selected_file[0])))
        for key, value in parse_results.paragraphs.items():
            document_cursor.insertText(value["text"])
            block_data = BlockUserData()
            for k, v in value["data"].items():
                block_data[k] = v
            document_cursor.block().setUserData(block_data)
            if "\n" in block_data["strokes"][-1][2]:
                document_cursor.insertText("\n")
            document_cursor.movePosition(QTextCursor.End)
        self.textEdit.setDocument(new_document)
        self.textEdit.moveCursor(QTextCursor.End)
        styles = []
        for k, v in parse_results.styles.items():
            styles.append(v["text"])
        style_dict = {}
        for k, v in parse_results.styles.items():
            style_name = v["text"]
            one_style_dict = {}
            try:
                one_style_dict["parentstylename"] = styles[v["sbasedon"]]
            except KeyError:
                pass
            try:
                one_style_dict["nextstylename"] = styles[v["snext"]]
            except KeyError:
                pass
            style_dict[style_name] = one_style_dict
        self.style_selector.clear()
        self.style_selector.addItems([*style_dict])
        self.styles = style_dict
        self.statusBar.showMessage("Finished loading transcript data from rtf {filename}".format(filename = str(selected_file[0])))
        log.info("Loading finished.")                
