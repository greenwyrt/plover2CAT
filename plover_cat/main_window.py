import os
import subprocess
import string
import re
import pathlib
import json
import textwrap
import html
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from collections import Counter
from shutil import copyfile
from math import trunc
from copy import deepcopy
from sys import platform
from spylls.hunspell import Dictionary
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository
from dulwich import porcelain
from odf.opendocument import OpenDocumentText, load
from odf.office import FontFaceDecls, Styles
from odf.style import (Style, TextProperties, ParagraphProperties, FontFace, PageLayout, 
PageLayoutProperties, MasterPage, TabStops, TabStop, GraphicProperties, Header, Footer)
from odf.text import H, P, Span, Tab, LinenumberingConfiguration, PageNumber
from odf.teletype import addTextToElement
from odf.draw import Frame, TextBox

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import (QBrush, QColor, QTextCursor, QFont, QFontMetrics, QTextDocument, 
QCursor, QStandardItem, QStandardItemModel, QPageSize, QTextBlock, QTextFormat, QTextBlockFormat, 
QTextOption, QTextCharFormat, QKeySequence)
from PyQt5.QtWidgets import (QMainWindow, QFileDialog, QInputDialog, QListWidgetItem, QTableWidgetItem, 
QStyle, QMessageBox, QFontDialog, QPlainTextDocumentLayout, QUndoStack, QLabel, QMenu,
QDockWidget, QVBoxLayout, QCompleter, QApplication, QTextEdit, QProgressBar, QAction)
from PyQt5.QtMultimedia import (QMediaContent, QMediaPlayer, QMediaMetaData, QMediaRecorder, 
QAudioRecorder, QMultimedia, QVideoEncoderSettings, QAudioEncoderSettings)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QFile, QTextStream, QUrl, QTime, QDateTime, QSettings, QRegExp, QSize, QStringListModel, QSizeF
_ = lambda txt: QtCore.QCoreApplication.translate("Plover2CAT", txt)

import plover

from plover.engine import StenoEngine
from plover.steno import Stroke, normalize_steno, normalize_stroke
from plover.dictionary.base import load_dictionary
from plover.registry import registry
from plover import log

from . __version__ import __version__
from plover_cat.plover_cat_ui import Ui_PloverCAT
from plover_cat.rtf_parsing import *
from plover_cat.constants import *
from plover_cat.qcommands import *
from plover_cat.stroke_funcs import *
from plover_cat.helpers import * 
  
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
        ## on very first startup, set tabs up
        ## later configs will use window settings
        self.tabifyDockWidget(self.dockHistoryStack, self.dockPaper)
        self.tabifyDockWidget(self.dockStenoData, self.dockAudio)
        settings = QSettings("Plover2CAT", "OpenCAT")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.contains("windowstate"):
            self.restoreState(settings.value("windowstate"))
        if settings.contains("windowfont"):
            font_string = settings.value("windowfont")
            font = QFont()
            font.fromString(font_string)
            self.setFont(font)
        if settings.contains("tapefont"):
            font_string = settings.value("tapefont")
            font = QFont()
            font.fromString(font_string)
            self.strokeList.setFont(font)
        self.config = {}
        self.file_name = ""
        self.styles = {}
        self.txt_formats = {}
        self.par_formats = {}
        self.speakers = {}
        self.styles_path = ""
        self.stroke_time = ""
        self.audio_file = ""
        self.cursor_block = 0
        self.cursor_block_position = 0
        self.last_raw_steno = ""
        self.last_string_sent = ""
        self.last_backspaces_sent = 0
        self.undo_stack = QUndoStack(self)
        self.undoView.setStack(self.undo_stack)
        self.cutcopy_storage = {}
        self.spell_ignore = []
        self.textEdit.setPlainText("Welcome to Plover2CAT\nOpen or create a transcription folder first with File->New...\nA timestamped transcript folder will be created.")
        self.menu_enabling()
        self.set_shortcuts()
        # connections:
        ## file setting/saving
        self.actionQuit.triggered.connect(lambda: self.action_close())
        self.actionNew.triggered.connect(lambda: self.create_new())
        self.actionClose.triggered.connect(lambda: self.close_file())
        self.actionOpen.triggered.connect(lambda: self.open_file())
        self.actionSave.triggered.connect(lambda: self.save_file())
        self.actionSaveAs.triggered.connect(lambda: self.save_as_file())
        self.actionOpenTranscriptFolder.triggered.connect(lambda: self.open_root())
        self.actionImportRTF.triggered.connect(lambda: self.import_rtf())
        ## audio connections
        self.actionOpenAudio.triggered.connect(lambda: self.open_audio())
        self.actionPlayPause.triggered.connect(self.play_pause)
        self.actionStopAudio.triggered.connect(self.stop_play)
        self.playRate.valueChanged.connect(self.update_playback_rate)
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_seeker_track)
        self.audio_seeker.sliderMoved.connect(self.set_position)
        self.actionSkipForward.triggered.connect(lambda: self.seek_position())
        self.actionSkipBack.triggered.connect(lambda: self.seek_position(-1))
        self.actionRecordPause.triggered.connect(lambda: self.record_or_pause())
        self.actionStopRecording.triggered.connect(lambda: self.stop_record())
        self.recorder.error.connect(lambda: self.recorder_error())
        self.recorder.durationChanged.connect(self.update_record_time)
        self.actionShowVideo.triggered.connect(lambda: self.show_hide_video())
        ## editor related connections
        self.actionClearParagraph.triggered.connect(lambda: self.reset_paragraph())
        self.textEdit.cursorPositionChanged.connect(self.display_block_data)
        self.textEdit.complete.connect(self.insert_autocomplete)
        self.editorCheck.stateChanged.connect(self.editor_lock)
        self.submitEdited.clicked.connect(self.edit_user_data)
        self.actionCopy.triggered.connect(lambda: self.copy_steno())
        self.actionCut.triggered.connect(lambda: self.cut_steno())
        self.actionPaste.triggered.connect(lambda: self.paste_steno())
        self.actionRedo.triggered.connect(self.undo_stack.redo)
        self.actionUndo.triggered.connect(self.undo_stack.undo)
        self.actionFindReplacePane.triggered.connect(lambda: self.show_find_replace())
        self.actionInsertNormalText.triggered.connect(self.insert_text)
        self.actionJumpToParagraph.triggered.connect(self.jump_par)
        self.actionWindowFont.triggered.connect(lambda: self.change_window_font())
        self.actionShowAllCharacters.triggered.connect(lambda: self.show_invisible_char())
        self.actionPaperTapeFont.triggered.connect(lambda: self.change_tape_font())
        self.textEdit.customContextMenuRequested.connect(self.context_menu)
        self.textEdit.send_del.connect(self.mock_del)
        self.parSteno.setStyleSheet("alternate-background-color: darkGray;")
        self.strokeList.setStyleSheet("selection-background-color: darkGray;")
        self.revert_version.clicked.connect(self.revert_file)
        ## steno related edits
        self.actionMergeParagraphs.triggered.connect(lambda: self.merge_paragraphs())
        self.actionSplitParagraph.triggered.connect(lambda: self.split_paragraph())
        self.actionAddCustomDict.triggered.connect(lambda: self.add_dict())
        self.actionRemoveTranscriptDict.triggered.connect(lambda: self.remove_dict())
        self.actionRetroactiveDefine.triggered.connect(lambda: self.define_retroactive())
        self.actionDefineLast.triggered.connect(lambda: self.define_scan())
        self.actionAutocompletion.triggered.connect(self.setup_completion)
        self.actionAddAutocompletionTerm.triggered.connect(self.add_autocomplete_item)
        self.actionTranslateTape.triggered.connect(self.tape_translate)
        ## style connections
        self.edit_page_layout.clicked.connect(self.update_config)
        self.editCurrentStyle.clicked.connect(self.style_edit)
        self.actionCreateNewStyle.triggered.connect(self.new_style)
        self.actionRefreshEditor.triggered.connect(self.refresh_editor_styles)
        self.actionStyleFileSelect.triggered.connect(self.select_style_file)
        self.actionGenerateStyleFromTemplate.triggered.connect(self.style_from_template)
        self.style_selector.activated.connect(self.update_paragraph_style)
        self.blockFont.currentFontChanged.connect(self.calculate_space_width)
        self.textEdit.ins.connect(self.change_style)
        ## search/replace connections
        self.search_text.toggled.connect(lambda: self.search_text_options())
        self.search_steno.toggled.connect(lambda: self.search_steno_options())
        self.search_untrans.toggled.connect(lambda: self.search_untrans_options())
        self.search_forward.clicked.connect(lambda: self.search())
        self.search_backward.clicked.connect(lambda: self.search(-1))
        self.replace_selected.clicked.connect(lambda: self.replace())
        self.replace_all.clicked.connect(lambda: self.replace_everything())
        ## spellcheck
        self.dictionary = Dictionary.from_files('en_US')
        self.spell_search.clicked.connect(lambda: self.spellcheck())
        self.spell_skip.clicked.connect(lambda: self.spellcheck())
        self.spell_ignore_all.clicked.connect(lambda: self.sp_ignore_all())
        self.spellcheck_suggestions.itemDoubleClicked.connect(self.sp_insert_suggest)
        self.dict_selection.activated.connect(self.set_sp_dict)
        ## tape
        self.textEdit.document().blockCountChanged.connect(lambda: self.get_suggestions())
        self.suggest_sort.toggled.connect(lambda: self.get_suggestions())
        self.numbers = {number: letter for letter, number in plover.system.NUMBERS.items()}
        self.strokeLocate.clicked.connect(lambda: self.stroke_to_text_move())
        self.textEdit.cursorPositionChanged.connect(lambda: self.text_to_stroke_move())
        # export
        self.actionPlainText.triggered.connect(lambda: self.export_text())
        self.actionASCII.triggered.connect(lambda: self.export_ascii())
        self.actionPlainASCII.triggered.connect(lambda: self.export_plain_ascii())
        self.actionHTML.triggered.connect(lambda: self.export_html())
        self.actionSubRip.triggered.connect(lambda: self.export_srt())
        self.actionODT.triggered.connect(lambda: self.export_odt())
        self.actionRTF.triggered.connect(lambda: self.export_rtf())
        # help
        self.actionUserManual.triggered.connect(lambda: self.open_help())
        self.actionAbout.triggered.connect(lambda: self.about())
        self.actionAcknowledgements.triggered.connect(lambda: self.acknowledge())
        # status bar
        self.statusBar.showMessage("Create New Transcript or Open Existing...")
        self.cursor_status = QLabel("Par,Char: {line},{char}".format(line = 0, char = 0))
        self.cursor_status.setObjectName("cursor_status")
        self.statusBar.addPermanentWidget(self.cursor_status)
        self.repo = None
        ## engine connections
        self.textEdit.setEnabled(True)
        engine.signal_connect("stroked", self.on_stroke) 
        engine.signal_connect("stroked", self.log_to_tape) 
        engine.signal_connect("send_string", self.on_send_string)
        engine.signal_connect("send_backspaces", self.count_backspaces)
        log.info("Main window open")

    def set_shortcuts(self):
        shortcut_file = pathlib.Path(plover.oslayer.config.CONFIG_DIR) / "plover2cat" / "shortcuts.json"
        if not shortcut_file.exists():
            log.debug("No shortcut file exists, using default menu shortcuts.")
            return
        else:
            with open(shortcut_file, "r") as f:
                shortcuts = json.loads(f.read())
        for identifier, keysequence in shortcuts.items():
            try:
                select_action = self.findChild(QAction, identifier)
                select_action.setShortcut(QKeySequence(keysequence)) 
            except:
                pass   
        # test_action = self.findChild(QAction, "actionSaveAs")
        # test_action.setShortcut(QKeySequence("Ctrl+L"))

    def about(self):
        QMessageBox.about(self, "About",
                "This is Plover2CAT version %s, a computer aided transcription plugin for Plover." % __version__)

    def acknowledge(self):
        QMessageBox.about(self, "Acknowledgements",
                        "Plover2CAT is built on top of Plover, the open source stenotype engine. "
                        "It owes its development to the members of the Plover discord group who provided suggestions and bug finding. "
                        "PyQt5 and Plover are both licensed under the GPL. Fugue icons are by Yusuke Kamiyamane, under the Creative Commons Attribution 3.0 License.")

    def setup_completion(self, checked):
        log.info("Setting up autocompletion.")
        if not checked:
            self.textEdit.setCompleter(None)
        self.completer = QCompleter(self)
        wordlist_path = self.file_name / "sources" / "wordlist.json"
        if not wordlist_path.exists():
            log.info("Wordlist does not exist.")
            QMessageBox.warning(self, "Autocompletion", "The required file wordlist.json is not available in the sources folder. See user manual for format.")
            self.statusBar.showMessage("Wordlist.json for autocomplete does not exist in sources directory. Passing")
            return
        self.completer.setModel(self.modelFromFile(str(wordlist_path)))
        self.completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWrapAround(False)
        self.textEdit.setCompleter(self.completer)
        self.statusBar.showMessage("Autocompletion from wordlist.json enabled.")

    def modelFromFile(self, fileName):
        f = QFile(fileName)
        if not f.open(QFile.ReadOnly):
            return(QStringListModel(self.completer))
        with open(fileName, "r") as f:
            completer_dict = json.loads(f.read())
        words = QStandardItemModel(self.completer)
        for key, value in completer_dict.items():
            item = QStandardItem()
            # removes any newlines/tabs, otherwise breaks autocomplete
            key = " ".join(key.split())
            item.setText(key)
            item.setData(value, QtCore.Qt.UserRole)
            words.appendRow(item)
        return(words)

    def add_autocomplete_item(self):
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            self.statusBar.showMessage("No text selected for autocomplete")
            return
        current_block = current_cursor.block()
        selected_text = current_cursor.selectedText()        
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        # end_pos is in prep for future multi-stroke untrans
        end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        start_stroke_pos = stroke_pos_at_pos(current_block.userData()["strokes"], start_pos)
        end_stroke_pos = stroke_pos_at_pos(current_block.userData()["strokes"], end_pos)
        underlying_strokes = extract_stroke_data(current_block.userData()["strokes"], start_stroke_pos[0], end_stroke_pos[1], copy = True)
        underlying_steno = "/".join([stroke[1] for stroke in underlying_strokes])
        text, ok = QInputDialog().getText(self, "Add Autocomplete Term", "Text: %s \nSteno:" % selected_text, text = underlying_steno)
        if not ok:
            return
        log.debug("Adding term to autocompletion")
        wordlist_path = self.file_name / "sources" / "wordlist.json"
        if wordlist_path.exists():
            with open(wordlist_path, "r") as f:
                completer_dict = json.loads(f.read())
        else:
            completer_dict = {}
        completer_dict[selected_text.strip()] = text
        save_json(completer_dict, wordlist_path)
        self.setup_completion(self.actionAutocompletion.isChecked())

    def open_help(self):
        user_manual_link = QUrl("https://github.com/greenwyrt/plover2CAT/tree/main/docs")
        QtGui.QDesktopServices.openUrl(user_manual_link)

    def menu_enabling(self, value = True):
        self.menuEdit.setEnabled(not value)
        self.menuSteno_Actions.setEnabled(not value)
        self.menuDictionary.setEnabled(not value)
        self.menuAudio.setEnabled(not value)
        self.menuStyling.setEnabled(not value)
        self.actionNew.setEnabled(value)
        self.actionSave.setEnabled(not value)
        self.actionSaveAs.setEnabled(not value)
        self.actionOpen.setEnabled(value)
        self.actionPlainText.setEnabled(not value)
        self.actionASCII.setEnabled(not value)
        self.actionSubRip.setEnabled(not value)
        self.actionHTML.setEnabled(not value)
        self.actionPlainASCII.setEnabled(not value)
        self.actionODT.setEnabled(not value)
        self.actionAddCustomDict.setEnabled(not value)
        self.actionMergeParagraphs.setEnabled(not value)
        self.actionSplitParagraph.setEnabled(not value)
        self.actionRetroactiveDefine.setEnabled(not value)
        self.actionDefineLast.setEnabled(not value)
        self.actionAddAutocompletionTerm.setEnabled(not value)
        self.actionCut.setEnabled(not value)
        self.actionCopy.setEnabled(not value)
        self.actionPaste.setEnabled(not value)
        self.actionPlayPause.setEnabled(not value)
        self.actionStopAudio.setEnabled(not value)
        self.actionRecordPause.setEnabled(not value)
        self.actionOpenTranscriptFolder.setEnabled(not value)
        self.actionImportRTF.setEnabled(not value)

    def context_menu(self, pos):
        menu = QMenu()
        menu.addAction(self.actionRetroactiveDefine)
        menu.addAction(self.actionMergeParagraphs)
        menu.addAction(self.actionSplitParagraph)
        menu.addAction(self.actionCut)
        menu.addAction(self.actionCopy)
        menu.addAction(self.actionPaste)
        menu.exec_(self.textEdit.viewport().mapToGlobal(pos))
    # open/close/save
    def create_new(self):
        ## make new dir, sets gui input
        project_dir = QFileDialog.getExistingDirectory(self, "Select Directory", plover.oslayer.config.CONFIG_DIR)
        if not project_dir:
            log.info("No directory selected, passing")
            return
        if not pathlib.Path(project_dir).exists:
            user_choice = QMessageBox.question(self, "Create New", "Specified file path does not exist. Create new?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.info("Creating new dir from provided path")
                pathlib.Path(project_dir).mkdir(parents = True)
            else:
                log.info("Abort new transcript creation because path does not exist.")
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
        with open(config_path, "w") as f:
            json.dump(default_config, f)
            log.info("Project configuration file created")
        self.config = self.load_config_file(transcript_dir_path)
        self.create_default_styles()
        style_file_name = transcript_dir_path / "styles/default.json"
        self.styles = self.load_check_styles(style_file_name)
        self.gen_style_formats()
        default_dict_path = transcript_dir_path / "dict"
        self.create_default_dict()
        export_path = transcript_dir_path / "export"
        os.mkdir(export_path)
        default_spellcheck_path = transcript_dir_path / "spellcheck"
        default_spellcheck_path.mkdir(parents=True)
        self.repo = Repo.init(str(transcript_dir_path))
        self.textEdit.clear()
        self.setup_page()
        self.strokeList.clear()
        # self.suggestTable.clearContents()
        self.menu_enabling(False)
        self.statusBar.showMessage("Created project.")
        log.info("New project successfully created and set up")
        self.update_paragraph_style()

    def open_file(self):
        name = "Config"
        extension = "config"
        selected_folder = QFileDialog.getOpenFileName( self, _("Open " + name), plover.oslayer.config.CONFIG_DIR, _(name + "(*." + extension + ")"))[0]
        if not selected_folder:
            log.info("No config file was selected for loading.")
            return
        selected_folder = pathlib.Path(selected_folder).parent
        ## one day, a modal here to make sure non-empty textedit saved before switching to existing file
        self.statusBar.showMessage("Opening project.")
        log.info("Loading project files from %s", str(selected_folder))
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")
        transcript_tape = selected_folder.joinpath(selected_folder.stem).with_suffix(".tape")
        self.file_name = selected_folder
        config_contents = self.load_config_file(selected_folder)
        log.debug("Config contents: %s", config_contents)
        self.config = config_contents
        self.textEdit.clear()
        self.strokeList.clear()
        # self.suggestTable.clearContents()
        style_path = selected_folder / config_contents["style"]
        log.info("Loading styles for transcript")
        self.styles = self.load_check_styles(style_path)
        self.gen_style_formats()
        self.set_dictionary_config(config_contents["dictionaries"])
        default_spellcheck_path = selected_folder / "spellcheck"
        if default_spellcheck_path.exists():
            available_dicts = [file.stem for file in default_spellcheck_path.iterdir() if str(file).endswith("dic")]
            if available_dicts:
                self.dict_selection.addItems(available_dicts)
        # self.setup_speaker_ids()
        current_cursor = self.textEdit.textCursor()
        if pathlib.Path(transcript_tape).is_file():
            log.info("Tape file found, loading.")
            self.statusBar.showMessage("Loading tape.")
            tape_file = QFile(str(transcript_tape))
            tape_file.open(QFile.ReadOnly|QFile.Text)
            istream = QTextStream(tape_file)
            self.strokeList.document().setPlainText(istream.readAll())
            self.strokeList.verticalScrollBar().setValue(self.strokeList.verticalScrollBar().maximum())
            log.info("Loaded tape.")
        if pathlib.Path(transcript).is_file():
            self.load_transcript(transcript)
            self.statusBar.showMessage("Finished loading transcript data.")         
        self.textEdit.setCursorWidth(5)
        self.textEdit.moveCursor(QTextCursor.End)
        self.setup_page()
        self.menu_enabling(False)
        export_path = selected_folder / "export"
        pathlib.Path(export_path).mkdir(parents = True, exist_ok=True)
        ## manually set first block data  
        new_block = self.textEdit.document().firstBlock()
        if not new_block.userData():
            block_dict = BlockUserData()
            block_dict["creationtime"] = datetime.now().isoformat("T", "milliseconds")
            new_block.setUserData(block_dict)
        log.info("Project files, if exist, have been loaded.")
        try:
            self.repo = Repo(selected_folder)
            self.dulwich_save()
        except NotGitRepository:
            self.repo = Repo.init(selected_folder)
        self.statusBar.showMessage("Setup complete. Ready for work.")
        if self.textEdit.document().characterCount() == 1:
            self.update_paragraph_style()

    def save_file(self):
        if not self.file_name:
            log.info("No project dir set, cannot save file.")
            return
        selected_folder = pathlib.Path(self.file_name)
        self.update_config()
        document_blocks = self.textEdit.document().blockCount()
        json_document = {}
        log.info("Extracting block data for transcript save")
        self.statusBar.showMessage("Saving transcript data.")
        block = self.textEdit.document().begin()
        while True:
            block_dict = block.userData().return_all()
            block_text = block.text()
            block_num = block.blockNumber()
            inner_dict =  {"text": block_text, "data": block_dict}
            # log.debug(inner_dict)
            json_document[block_num] = inner_dict
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()          
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")
        log.info("Saving transcript data to %s", str(transcript))
        save_json(json_document, transcript)
        if str(self.styles_path).endswith(".json"):
            save_json(self.styles, self.styles_path)
        self.textEdit.document().setModified(False)
        self.undo_stack.setClean()
        self.dulwich_save(message = "user save")
        self.statusBar.showMessage("Saved project data")  

    def dulwich_save(self, message = "autosave"):
        transcript_dicts = self.file_name / "dict"
        available_dicts = [transcript_dicts / file for file in transcript_dicts.iterdir()]
        transcript = self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript")
        transcript_tape = self.file_name.joinpath(self.file_name.stem).with_suffix(".tape")
        files = [transcript, transcript_tape] + available_dicts
        # add files, regardless of modified, to stage
        porcelain.add(self.repo.path, paths = files)
        # commit
        porcelain.commit(self.repo, message = message, author = "plover2CAT <fake_email@fakedomain.com>", committer= "plover2CAT <fake_email@fakedomain.com>")
        commit_choices = return_commits(self.repo)
        self.versions.clear()
        for commit_id, commit_time in commit_choices:
            self.versions.addItem(commit_time, commit_id)            

    def load_transcript(self, transcript):
        log.info("Transcript file found, loading")
        with open(transcript, "r") as f:
            self.statusBar.showMessage("Reading transcript data.")
            json_document = json.loads(f.read())
        self.textEdit.moveCursor(QTextCursor.Start)
        document_cursor = self.textEdit.textCursor()
        self.statusBar.showMessage("Loading transcript data.")
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(json_document))
        self.progressBar.setFormat("Load transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.textEdit.blockSignals(True)
        self.textEdit.document().blockSignals(True)
        for key, value in json_document.items():
            document_cursor.insertText(value["text"])
            block_data = BlockUserData()
            for k, v in value["data"].items():
                block_data[k] = v
            document_cursor.block().setUserData(block_data)
            if len(block_data["strokes"]) > 0 and "\n" in block_data["strokes"][-1][2]:
                document_cursor.insertText("\n")
            self.progressBar.setValue(document_cursor.blockNumber())
            QApplication.processEvents()
        self.textEdit.document().blockSignals(True)
        self.textEdit.blockSignals(False)
        self.refresh_editor_styles()
        self.statusBar.removeWidget(self.progressBar)
        log.info("Loaded transcript.")   

    def revert_file(self):
        if not self.repo:
            return
        QMessageBox.warning(self, "Revert", "The transcript will be reverted back to the version on %s. All unsaved changes will be destroyed. Session history will be erased. Do you wish to continue?" % self.versions.itemText(self.versions.currentIndex()))
        selected_commit_id = self.versions.itemData(self.versions.currentIndex())
        transcript = str(self.file_name.stem) + (".transcript")
        porcelain.reset_file(self.repo, transcript, selected_commit_id)
        new_commit_message = "revert to %s" % selected_commit_id.decode("ascii")
        self.dulwich_save(message=new_commit_message)
        self.undo_stack.clear()
        transcript = self.file_name.joinpath(self.file_name.stem).with_suffix(".transcript")
        self.textEdit.clear()
        if pathlib.Path(transcript).is_file():
            self.load_transcript(transcript)
        self.textEdit.setCursorWidth(5)
        self.textEdit.moveCursor(QTextCursor.End)

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
        self.statusBar.showMessage("Saving transcript data.")
        block = self.textEdit.document().begin()
        # start_time = perf_counter() 
        while True:
            block_dict = block.userData().return_all()
            block_text = block.text()
            block_num = block.blockNumber()
            inner_dict =  {"text": block_text, "data": block_dict}
            # log.debug(inner_dict)
            json_document[block_num] = inner_dict
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()  
        save_json(json_document, transcript)             
        log.info("Transcript data saved in new location" + str(transcript))
        with open(transcript_tape, "w") as f:
            f.write(tape_contents)
            log.info("Tape data saved in new location" + str(transcript_tape))
        self.file_name = transcript_dir_path
        self.setWindowTitle(str(self.file_name))
        self.textEdit.document().setModified(False)
        self.statusBar.showMessage("Saved transcript data")

    def close_file(self):
        if not self.undo_stack.isClean():
            user_choice = QMessageBox.question(self, "Close", "Are you sure you want to close without saving changes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.info("User choice to close without saving")
                pass
            else:
                log.info("Abort project close because of unsaved changes.")
                return False
        # restore dictionaries back to original
        self.restore_dictionary_from_backup()
        if self.recorder.status() == QMediaRecorder.RecordingState:
            self.stop_record()
        ## resets textedit and vars
        self.file_name = ""
        self.cursor_block = 0
        self.cursor_block_position = 0        
        self.menu_enabling()
        self.textEdit.setPlainText("Welcome to Plover2CAT\nSet up or create a transcription folder first with File->New...\nA timestamped transcript folder will be created.")        
        self.strokeList.clear()
        self.suggestTable.clearContents()
        self.undo_stack.clear()
        self.parSteno.clear()
        self.statusBar.showMessage("Project closed")
        return True

    def action_close(self):
        log.info("User selected quit.")
        settings = QSettings("Plover2CAT", "OpenCAT")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowstate", self.saveState())
        settings.setValue("windowfont", self.font().toString())
        settings.setValue("tapefont", self.strokeList.font().toString())
        log.info("Saved window settings")
        choice = self.close_file()
        if choice:
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
        selected_folder = self.file_name
        dict_dir = selected_folder / "dict"
        dict_file_name = "default.json"
        dict_file_name = dict_dir / dict_file_name
        log.info("Creating default dictionary in %s", str(dict_file_name))
        save_json(default_dict, dict_file_name)
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
        if "page_line_numbering" in config_contents:
            self.enable_line_num.setChecked(config_contents["page_line_numbering"])
        if "page_linenumbering_increment" in config_contents:
            self.line_num_freq.setValue(int(config_contents["page_linenumbering_increment"]))
        if "page_timestamp" in config_contents:
            self.enable_timestamp.setChecked(config_contents["page_timestamp"])
        if "page_max_char" in config_contents:
            self.page_max_char.setValue(int(config_contents["page_max_char"]))
        if "page_max_line" in config_contents:
            self.page_max_lines.setValue(int(config_contents["page_max_line"]))
        if "header_left" in config_contents:
            self.header_left.setText(config_contents["header_left"])
        if "header_center" in config_contents:
            self.header_center.setText(config_contents["header_center"])
        if "header_right" in config_contents:
            self.header_right.setText(config_contents["header_right"])
        if "footer_left" in config_contents:
            self.footer_left.setText(config_contents["footer_left"])
        if "footer_center" in config_contents:
            self.footer_center.setText(config_contents["footer_center"])
        if "footer_right" in config_contents:
            self.footer_right.setText(config_contents["footer_right"])
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
        config_contents["page_linenumbering_increment"] = self.line_num_freq.value()
        config_contents["page_timestamp"] = self.enable_timestamp.isChecked()
        config_contents["page_max_char"] = self.page_max_char.value()
        config_contents["page_max_line"] = self.page_max_lines.value()
        config_contents["header_left"] = self.header_left.text()
        config_contents["header_center"] = self.header_center.text()
        config_contents["header_right"] = self.header_right.text()
        config_contents["footer_left"] = self.footer_left.text()
        config_contents["footer_center"] = self.footer_center.text()
        config_contents["footer_right"] = self.footer_right.text()
        self.config = config_contents
        log.debug(config_contents)
        self.save_config(self.file_name)
        self.setup_page()

    def save_config(self, dir_path):
        config_path = pathlib.Path(dir_path) / "config.CONFIG"
        log.info("Saving config to " + str(config_path))
        config_contents = self.config
        style_path = pathlib.Path(self.styles_path)
        config_contents["style"] = str(style_path.relative_to(self.file_name))
        with open(config_path, "w") as f:
            json.dump(config_contents, f)
            log.info("Config saved")
            self.statusBar.showMessage("Saved config data")
    # style related
    def setup_page(self):
        doc = self.textEdit.document()
        width = float(self.config["page_width"])
        height = float(self.config["page_height"])
        log.info("Setting editor page size to %sin and %sin (WxH)." % (str(width), str(height)))
        width_pt = int(in_to_pt(width))
        height_pt = int(in_to_pt(height))
        self.textEdit.setLineWrapMode(QTextEdit.FixedPixelWidth)
        self.textEdit.setLineWrapColumnOrWidth(width_pt)
        page_size = QPageSize(QSizeF(width, height), QPageSize.Inch, matchPolicy = QPageSize.FuzzyMatch) 
        # print(page_size.size(QPageSize.Point).width())
        doc.setPageSize(page_size.size(QPageSize.Point))

    def create_default_styles(self):
        log.info("Create default styles for project")
        selected_folder = self.file_name
        style_dir = selected_folder / "styles"
        style_file_name = "default.json"
        style_file_name = style_dir / style_file_name
        save_json(default_styles, style_file_name)
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
            json_styles = load_odf_styles(path)
        else:
            log.info("Loading JSON style file from %s", str(path))
            # this only checks first level keys, one day, should use the data from this [attribute[1] for attribute in Style(name = "Name").allowed_attributes()],  [attribute[1] for attribute in TextProperties().allowed_attributes()], [attribute[1] for attribute in ParagraphProperties().allowed_attributes()] 
            acceptable_keys = {'styleindex', 'autoupdate', 'class', 'datastylename', 'defaultoutlinelevel', 'displayname', 'family', 'listlevel', 'liststylename', 'masterpagename', 'name', 'nextstylename', 'parentstylename', 'percentagedatastylename', "paragraphproperties", "textproperties"}
            with open(path, "r") as f:
                json_styles = json.loads(f.read())
            for k, v in json_styles.items():
                sub_keys = set([*v])
                if not sub_keys.issubset(acceptable_keys):
                    log.info("Some first-level keys in style json are not valid.")
                    log.debug("First-level keys: %s" % sub_keys)
                    self.statusBar.showMessage("Style file failed to parse.")
                    return False
        # clear old styles out before loading from new styles
        self.style_selector.clear()
        log.debug(json_styles)
        self.style_selector.addItems([*json_styles])
        self.statusBar.showMessage("Loaded style data.")
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

    def gen_style_formats(self):
        # call each time style change occurs
        styles_json = self.styles
        txt_formats = {}
        par_formats = {}
        log.info("Style: creating block and text formats.")
        for k, v in styles_json.items():
            # print(k)
            style_par = recursive_style_format(styles_json, k, prop = "paragraphproperties")
            # print(style_par)
            style_txt = recursive_style_format(styles_json, k, prop = "textproperties")
            # print(style_txt)
            par_formats[k] = parprop_to_blockformat(style_par)
            txt_formats[k] = txtprop_to_textformat(style_txt)
        self.txt_formats = txt_formats
        self.par_formats = par_formats

    def select_style_file(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Style JSON or odt"),
            str(self.file_name), _("Style (*.json *.odt)"))[0]
        if not selected_file:
            return
        log.info("User selected style file at %s" % selected_file)
        self.styles = self.load_check_styles(selected_file)
        self.gen_style_formats()

    def style_from_template(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Style ODT or RTF/CRE file"),
            str(self.file_name), _("Style template file (*.odt *.rtf)"))[0]
        if not selected_file:
            return  
        log.info("User selected style template %s" % selected_file)
        if selected_file.endswith("odt"):
            json_styles = load_odf_styles(selected_file)
            self.statusBar.showMessage("Extracted ODF styles to styles folder.")
        elif selected_file.endswith("rtf"):
            self.statusBar.showMessage("Parsing RTF.")
            self.progressBar = QProgressBar(self)
            self.statusBar.addWidget(self.progressBar)
            parse_results = rtf_steno(selected_file, self.progressBar)
            parse_results.parse_document()
            json_styles, renamed_indiv_style = load_rtf_styles(parse_results)
            self.statusBar.showMessage("Extracted RTF styles to styles folder.")
        style_file_path = self.file_name / "styles" / pathlib.Path(pathlib.Path(selected_file).name).with_suffix(".json")
        save_json(remove_empty_from_dict(json_styles), style_file_path)

    def change_window_font(self):
        font, valid = QFontDialog.getFont()
        if valid:
            self.setFont(font)
            log.info("Font set for window")       

    def change_tape_font(self):
        font, valid = QFontDialog.getFont()
        if valid:
            self.strokeList.setFont(font)
            log.info("Font set for paper tape.")

    def show_invisible_char(self):
        doc_options = self.textEdit.document().defaultTextOption()
        if self.actionShowAllCharacters.isChecked():        
            doc_options.setFlags(doc_options.flags() | QTextOption.ShowTabsAndSpaces | QTextOption.ShowLineAndParagraphSeparators)
        else:
            doc_options.setFlags(doc_options.flags() & ~QTextOption.ShowTabsAndSpaces & ~QTextOption.ShowLineAndParagraphSeparators)
        self.textEdit.document().setDefaultTextOption(doc_options)
        
    def calculate_space_width(self, font):
        new_font = font
        new_font.setPointSize(self.blockFontSize.value())
        metrics = QFontMetrics(new_font)
        space_space = metrics.averageCharWidth()
        self.fontspaceInInch.setValue(round(pixel_to_in(space_space), 2))

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
        else:
            self.editorAudioStart.setTime(QTime(0, 0, 0, 0))
        if block_data["audioendtime"]:
            self.editorAudioEnd.setTime(QTime.fromString(block_data["audioendtime"], "HH:mm:ss.zzz"))
        else:
            self.editorAudioEnd.setTime(QTime(0, 0, 0, 0))
        if block_data["notes"]:
            self.editorNotes.setText(block_data["notes"])
        else:
            self.editorNotes.clear()
        if block_data["style"]:
            self.style_selector.setCurrentText(block_data["style"])
            self.update_style_display(block_data["style"])
        else:
            self.to_next_style()
            self.update_style_display(self.style_selector.currentText())
        self.cursor_status.setText("Par,Char: {line},{char}".format(line = block_number, char = current_cursor.positionInBlock())) 
        if block_data["strokes"]:
            self.display_block_steno(block_data["strokes"])
        self.textEdit.showPossibilities()

    def display_block_steno(self, strokes):
        # clear of last block data
        self.parSteno.clear()
        if len(strokes) > 0:
            if not all(isinstance(el, list) for el in strokes):
                strokes = [strokes]
        steno_names = ["%s\n%s" % (stroke[1], stroke[2]) for stroke in strokes]
        self.parSteno.addItems(steno_names)

    def update_paragraph_style(self):
        current_cursor = self.textEdit.textCursor()
        style_cmd = set_par_style(current_cursor.blockNumber(), self.style_selector.currentText(), self.textEdit, self.par_formats, self.txt_formats)
        self.undo_stack.push(style_cmd)
        self.update_style_display(self.style_selector.currentText())

    def update_style_display(self, style):
        block_style = self.par_formats[style]
        text_style = self.txt_formats[style]
        self.blockFont.setCurrentFont(text_style.font())
        self.blockFontSize.setValue(int(text_style.fontPointSize()))
        self.blockFontBold.setChecked(text_style.font().bold())
        self.blockFontItalic.setChecked(text_style.font().italic())
        self.blockFontUnderline.setChecked(text_style.font().underline())
        self.blockAlignment.setExclusive(False)
        for but in self.blockAlignment.buttons():
            but.setChecked(False)
        if block_style.alignment() == Qt.AlignJustify:
            self.blockJustify.setChecked(True)
        elif block_style.alignment() == Qt.AlignRight:
            self.blockRightAlign.setChecked(True)
        elif block_style.alignment() == Qt.AlignHCenter:
            self.blockCenterAlign.setChecked(True)
        else:
            self.blockLeftAlign.setChecked(True)
        self.blockAlignment.setExclusive(True)
        tabs = block_style.tabPositions()
        if len(tabs) > 1:
            self.blockTabStop.setEnabled(False)
            self.blockTabStop.setValue(0)
            tabs_in = [str(pixel_to_in(t.position)) for t in tabs]
            self.blockTabStop.setSpecialValueText(",".join(tabs_in))
        elif len(tabs) == 1:
            self.blockTabStop.setEnabled(True)
            self.blockTabStop.setSpecialValueText("")
            self.blockTabStop.setValue(pixel_to_in(tabs[0].position))
        else:
            self.blockTabStop.setEnabled(True)
            self.blockTabStop.setSpecialValueText("")
            self.blockTabStop.setValue(0)
        text_indent = block_style.textIndent() if block_style.textIndent() else 0
        left_margin = block_style.leftMargin() if block_style.leftMargin() else 0
        right_margin = block_style.rightMargin() if block_style.rightMargin() else 0
        top_margin = block_style.topMargin() if block_style.topMargin() else 0
        bottom_margin = block_style.bottomMargin() if block_style.bottomMargin() else 0
        line_spacing = int(block_style.lineHeight() if block_style.lineHeight() else 100)
        self.blockTextIndent.setValue(pixel_to_in(text_indent))
        self.blockLeftMargin.setValue(pixel_to_in(left_margin))
        self.blockRightMargin.setValue(pixel_to_in(right_margin))
        self.blockTopMargin.setValue(pixel_to_in(top_margin))
        self.blockBottomMargin.setValue(pixel_to_in(bottom_margin))
        self.blockLineSpace.setValue(line_spacing)
        ## todo: headinglevel
        self.blockParentStyle.clear()
        self.blockParentStyle.addItems([*self.styles])
        if "parentstylename" in self.styles[style]:
            self.blockParentStyle.setCurrentText(self.styles[style]["parentstylename"])
        else:
            self.blockParentStyle.setCurrentIndex(-1)
        self.blockNextStyle.clear()
        self.blockNextStyle.addItems([*self.styles])
        if "nextstylename" in self.styles[style]:
            self.blockNextStyle.setCurrentText(self.styles[style]["nextstylename"])
        else:
            self.blockNextStyle.setCurrentIndex(-1)

    def style_edit(self):
        style_name = self.style_selector.currentText()
        log.info("Editing style %s" % style_name)
        new_style_dict = {"family": "paragraph"}
        if self.blockParentStyle.currentIndex() != -1:
            # this is important so a style is not based on itself
            if self.blockParentStyle.currentText() != style_name:
                new_style_dict["parentstylename"] = self.blockParentStyle.currentText()
        if self.blockNextStyle.currentIndex() != -1:
            new_style_dict["nextstylename"] = self.blockNextStyle.currentText()
        # compare par and text properties to recursive original format
        original_style_par = recursive_style_format(self.styles, style_name, prop = "paragraphproperties")
        original_style_txt = recursive_style_format(self.styles, style_name, prop = "textproperties")
        log.debug("Old paragraph properties: %s" % original_style_par)
        log.debug("Old text properties: %s" % original_style_txt)
        new_txt_dict = {"fontname": self.blockFont.currentFont().family(), "fontfamily": self.blockFont.currentFont().family(), 
                        "fontsize": "%spt" % self.blockFontSize.value(), "fontweight": "bold" if self.blockFontBold.isChecked() else "", 
                        "fontstyle": "italic" if self.blockFontItalic.isChecked() else "", 
                        "textunderlinetype": "single" if self.blockFontUnderline.isChecked() else "", 
                        "textunderlinestyle": "solid" if self.blockFontUnderline.isChecked() else ""}
        # todo tabstop
        if self.blockJustify.isChecked():
            textalign = "justify"
        elif self.blockRightAlign.isChecked():
            textalign = "right"
        elif self.blockCenterAlign.isChecked():
            textalign = "center"
        else:
            textalign = "left"       
        new_par_dict = {"textalign": textalign, "textindent": "%.2fin" % self.blockTextIndent.value(), 
                        "marginleft": "%.2fin" % self.blockLeftMargin.value(), "marginright": "%.2fin" % self.blockRightMargin.value(), 
                        "margintop": "%.2fin" % self.blockTopMargin.value(), "marginbottom": "%.2fin" % self.blockBottomMargin.value(), 
                        "linespacing": "%d%%" % self.blockLineSpace.value()}
        if self.blockTabStop.isEnabled():
            # the input is disabled with multiple tabstops
            tab_pos = self.blockTabStop.value() if self.blockTabStop.value() != 0 else None
            # do not set if tabstop = 0, weird things might happen
            if tab_pos:
                new_par_dict["tabstop"] = "%.2fin" % tab_pos
        original_style_txt.update(new_txt_dict)
        original_style_txt = remove_empty_from_dict(original_style_txt)
        original_style_par.update(new_par_dict)
        log.debug("New paragraph properties: %s" % original_style_par)
        log.debug("New text properties: %s" % original_style_txt)
        new_style_dict["paragraphproperties"] = original_style_par
        new_style_dict["textproperties"] = original_style_txt
        log.debug("Style: new style dict %s" % new_style_dict)
        self.styles[style_name] = new_style_dict
        self.gen_style_formats()
        self.refresh_editor_styles()

    def new_style(self):
        log.info("Creating new style")
        text, ok = QInputDialog().getText(self, "Create New Style", "Style Name (based on %s)" % self.style_selector.currentText(), inputMethodHints  = Qt.ImhLatinOnly)
        if not ok:
            log.info("User cancelled style creation")
            return
        log.debug("Creating new style %s" % text.strip())
        self.styles[text.strip()] = {"family": "paragraph", "parentstylename": self.style_selector.currentText()}
        self.gen_style_formats()
        if str(self.styles_path).endswith(".json"):
            save_json(self.styles, self.styles_path)
        old_style = self.style_selector.currentText()
        self.style_selector.clear()
        self.style_selector.addItems([*self.styles])
        self.style_selector.setCurrentText(old_style)

    def refresh_editor_styles(self):
        block = self.textEdit.document().begin()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(self.textEdit.document().blockCount())
        self.progressBar.setFormat("Re-style paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.undo_stack.beginMacro("Refresh editor.")
        while True:
            try:
                block_style = block.userData()["style"]
            except TypeError:
                block_style = ""
            style_cmd = set_par_style(block.blockNumber(), block_style, self.textEdit, self.par_formats, self.txt_formats)
            self.undo_stack.push(style_cmd)
            self.progressBar.setValue(block.blockNumber())
            QApplication.processEvents()
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()
        self.undo_stack.endMacro()
        self.statusBar.removeWidget(self.progressBar)

    def to_next_style(self):
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        if current_cursor.blockNumber() == 0:
            return
        style_data = self.styles
        if len(style_data) == 0:
            return
        # keep using style as default if nothing is set
        previous_style = None
        new_style = self.style_selector.currentText()
        previous_block = current_block.previous()
        if previous_block:
            previous_dict = previous_block.userData()
            previous_style = previous_dict["style"]
        if previous_style and "nextstylename" in style_data[previous_style]:
            new_style = style_data[previous_style]["nextstylename"]
        # block_dict = update_user_data(block_dict, key = "style", value = new_style)
        self.style_selector.setCurrentText(new_style)
        style_cmd = set_par_style(current_cursor.blockNumber(), self.style_selector.currentText(), self.textEdit, self.par_formats, self.txt_formats)
        self.undo_stack.push(style_cmd)
        self.statusBar.showMessage("Paragraph style set to {style}".format(style = new_style))

    def change_style(self, index):
        self.style_selector.setCurrentIndex(qt_key_nums[index])
        print(qt_key_nums[index])
        current_cursor = self.textEdit.textCursor()
        style_cmd = set_par_style(current_cursor.blockNumber(), self.style_selector.currentText(), self.textEdit, self.par_formats, self.txt_formats)
        self.undo_stack.push(style_cmd)

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
        # log.debug(block_data.return_all())
        self.textEdit.document().findBlockByNumber(self.cursor_block).setUserData(block_data)
        self.statusBar.showMessage("Updated paragraph {par_num} data".format(par_num = self.cursor_block))

    def jump_par(self):
        current_cursor = self.textEdit.textCursor()
        max_blocks = self.textEdit.document().blockCount()
        current_block_num = current_cursor.blockNumber()
        block_num, ok = QInputDialog().getInt(self, "Jump to paragraph...", "Paragraph (0-based): ", current_block_num, 0, max_blocks)
        if ok:
            new_block = self.textEdit.document().findBlockByNumber(block_num)
            current_cursor.setPosition(new_block.position())
            self.textEdit.setTextCursor(current_cursor)
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
        if not tapey_tape_location.exists():
            return
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

    def get_clippy(self):
        '''This uses a modified clippy_2 Org format that inserts a |
        before the suggestions for ease of parsing.
        Ideally I'd load a specific transcript-specific clippy_2 output
        but that's currently beyond me since I have zero clue
        how I would dynamically load settings into another plugin
        from this one, short of bundling my own copy of it'''
        config_dir = pathlib.Path(plover.oslayer.config.CONFIG_DIR)
        clippy_location = config_dir.joinpath('clippy_2.org')
        log.debug("Trying to load clippy from default location")
        if not clippy_location.exists():
            log.debug("Clippy load failed")
            return
        raw_lines = [line for line in open(clippy_location)]
        stroke_search = []
        for line in raw_lines:
            line = ansi_escape.sub('', line) # strip color codes
            search_hit = re.search(r'\|\s+(.*)\s+<', line)
            if search_hit:
                  stroke_search.append(search_hit.group(1).split(", "))
        first_stroke_search = [x[0] for x in stroke_search] # TODO: show multiple suggestions per phrase
        log.debug("stroke_search = " + str(stroke_search))
        if self.suggest_sort.isChecked():
            most_common_strokes = [word for word, word_count in Counter(first_stroke_search).items() if word_count > 1]
            most_common_strokes = most_common_strokes[:min(11, len(most_common_strokes) + 1)]
            most_common_strokes = most_common_strokes[::-1]
        else: 
            most_common_strokes= [word for word, word_count in Counter(first_stroke_search).most_common(10) if word_count > 1]
        log.debug("most_common_strokes = " + str(most_common_strokes))
        words = [self.engine.lookup(tuple(stroke.split("/"))) for stroke in most_common_strokes]
        log.debug("words = " + str(words))
        self.suggestTable.clearContents()
        self.suggestTable.setRowCount(len(words))
        self.suggestTable.setColumnCount(2)
        for row in range(len(words)):
            self.suggestTable.setItem(row, 0, QTableWidgetItem(words[row]))
            self.suggestTable.setItem(row, 1, QTableWidgetItem(most_common_strokes[row]))
        self.suggestTable.resizeColumnsToContents()

    def get_suggestions(self):
        # self.get_tapey_tape()
        self.get_clippy()

    def stroke_to_text_move(self):
        stroke_cursor = self.strokeList.textCursor()
        edit_cursor = self.textEdit.textCursor()
        self.textEdit.blockSignals(True)
        try:
            stroke_cursor.movePosition(QTextCursor.StartOfBlock)
            stroke_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor_position_stroke = stroke_cursor.selectedText().split("|")[2].split(",")
            par = int(cursor_position_stroke[0].replace("(", ""))
            col = int(cursor_position_stroke[1].replace(")", ""))
            edit_cursor.movePosition(QTextCursor.Start)
            for i in range(par):
                edit_cursor.movePosition(QTextCursor.NextBlock)
            for i in range(col):
                edit_cursor.movePosition(QTextCursor.NextCharacter)
            self.textEdit.setTextCursor(edit_cursor)
        except:
            pass
        self.textEdit.blockSignals(False)

    def text_to_stroke_move(self):
        stroke_cursor = self.strokeList.textCursor()
        edit_cursor = self.textEdit.textCursor()
        edit_block = edit_cursor.block()
        # print(edit_block.blockFormatIndex())
        block_data = edit_block.userData()
        self.strokeList.blockSignals(True)
        stroke_text = self.strokeList.document().toPlainText().split("\n")
        pos = edit_cursor.positionInBlock()
        log.debug("Cursor at %d" % pos)
        try:
            if edit_cursor.atBlockStart():
                stroke_time = block_data["strokes"][0][0]
                stroke = block_data["strokes"][0][1]
            elif edit_cursor.atBlockEnd():
                stroke_time = block_data["strokes"][-1][0]
                stroke = block_data["strokes"][0][1]
            else:
                before, after = split_stroke_data(block_data["strokes"], pos)
                stroke_time = before[-1][0]
                stroke = block_data["strokes"][0][1]
            # no idea how fast this will be with many many more lines
            for index, i in enumerate(stroke_text):
                if i.startswith(stroke_time):
                    stroke_pos = index
            stroke_cursor.movePosition(QTextCursor.Start)
            for i in range(stroke_pos):
                stroke_cursor.movePosition(QTextCursor.NextBlock)
            stroke_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            self.strokeList.setTextCursor(stroke_cursor)
            self.strokeList.setCursorWidth(5)
            self.strokeList.ensureCursorVisible()
        except:
            pass
        self.strokeList.blockSignals(False)
    # steno functions
    def tape_translate(self):
        if not self.engine.output:
            self.statusBar.showMessage("Plover is not enabled.")
            return
        # do not erase any content before, case of too many asterisks for example
        self.engine.clear_translator_state()
        # bit of a hack since triggering stroked hook through code
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select tape file to translate"),
            str(self.file_name), _("Tape (*.tape *.txt)"))[0]
        if not selected_file:
            return
        transcript_dir = self.file_name 
        if pathlib.Path(selected_file) == transcript_dir.joinpath(transcript_dir.stem).with_suffix(".tape"):
            self.statusBar.showMessage("Cannot translate from own transcript tape.")
            return
        selected_file = pathlib.Path(selected_file)
        log.debug("Translating tape from %s" % selected_file)    
        paper_format, ok = QInputDialog.getItem(self, "Translate Tape", "Format of tape file:", ["Plover2CAT", "Plover (raw)", "Plover (paper)"], editable = False)
        if paper_format == "Plover (raw)":
            with open(selected_file) as f:
                for line in f:
                    stroke = Stroke(normalize_stroke(line.strip().replace(" ", "")))
                    self.engine._translator.translate(stroke)
                    self.engine._trigger_hook('stroked', stroke)
        elif paper_format == "Plover2CAT":
            with open(selected_file) as f:
                for line in f:
                    stroke_contents = line.strip().split("|")[3]
                    keys = []
                    for i in range(len(stroke_contents)):
                        if not stroke_contents[i].isspace() and i < len(plover.system.KEYS):
                            keys.append(plover.system.KEYS[i])                    
                    self.engine._translator.translate(Stroke(keys))
                    self.engine._trigger_hook('stroked', Stroke(keys))
        elif paper_format == "Plover (paper)":
            with open(selected_file) as f:
                for line in f:
                    keys = []
                    for i in range(len(line)):
                        if not line[i].isspace() and i < len(plover.system.KEYS):
                            keys.append(plover.system.KEYS[i])
                    self.engine._translator.translate(Stroke(keys))
                    self.engine._trigger_hook('stroked', Stroke(keys))
        # todo, if format has time data, that should be inserted into stroke data of editor too

    def on_stroke(self, stroke_pressed):
        self.editorCheck.setChecked(True)
        if not self.engine.output:
            return
        if not self.file_name:
            return
        # do nothing if window not in focus
        if not self.textEdit.isActiveWindow() and not self.actionCaptureAllOutput.isChecked():
            return
        if not self.last_string_sent and self.last_backspaces_sent == 0:
            return
        current_document = self.textEdit
        current_cursor = current_document.textCursor()
        if self.actionCursorAtEnd.isChecked():
            current_cursor.movePosition(QTextCursor.End)
            self.textEdit.setTextCursor(current_cursor)
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
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
        if len(focus_block.text()) == 0 and not string_sent and backspaces_sent > 0:
            focus_block = focus_block.previous()
            # if this is first block, nothing happens
            if not focus_block:
                return
        block_dict = focus_block.userData()
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
        block_dict["strokes"] = strokes_data
        focus_block.setUserData(block_dict)
        if backspaces_sent != 0 and not current_cursor.atEnd():
            cursor_pos = current_cursor.positionInBlock()
            remaining_text_len = len(focus_block.text()) - cursor_pos
            holding_space = backspaces_sent
            self.undo_stack.beginMacro("Remove")
            if holding_space > cursor_pos:
                initial_block = current_cursor.blockNumber()
                initial_block_pos = cursor_pos
                # check if backspacing to start of document
                if holding_space > current_cursor.position():
                    final_block = 0
                    final_block_pos = 0
                else:
                    current_cursor.setPosition(current_cursor.position() - holding_space)
                    final_block = current_cursor.blockNumber()
                    final_block_pos = current_cursor.positionInBlock()
                coords = [0] * (initial_block-final_block) + [final_block_pos]
                print(coords)
                current_cursor.setPosition(self.textEdit.document().findBlockByNumber(initial_block).position() + initial_block_pos)
                for seg, coords in zip(list(range(initial_block, final_block-1, -1)), coords):
                    self.textEdit.setTextCursor(current_cursor)
                    if coords == 0:
                        current_cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
                        self.textEdit.setTextCursor(current_cursor)
                        # print(current_cursor.text())
                        self.cut_steno(store=False)
                        self.merge_paragraphs(add_space = False)
                        current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor, remaining_text_len)
                    else:
                        current_cursor.setPosition(self.textEdit.document().findBlockByNumber(seg).position() + final_block_pos, QTextCursor.KeepAnchor)
                        self.textEdit.setTextCursor(current_cursor)
                        self.cut_steno(store=False)
                self.last_backspaces_sent = 0
            current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, self.last_backspaces_sent)
            self.textEdit.setTextCursor(current_cursor)
            self.cut_steno(store=False)
            self.last_backspaces_sent = 0
            self.undo_stack.endMacro()
            current_cursor = self.textEdit.textCursor()
            self.cursor_block = current_cursor.blockNumber()
            self.cursor_block_position = current_cursor.positionInBlock()
            return         
        if self.last_backspaces_sent != 0:
            stroke = [self.stroke_time, raw_steno, ""]
            if self.player.state() == QMediaPlayer.PlayingState: stroke.append(real_time)
            if self.recorder.state() == QMediaRecorder.RecordingState: stroke.append(real_time)
            current_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, backspaces_sent)
            deleted_text = current_cursor.selectedText()
            start_pos = min(current_cursor.position(), current_cursor.anchor()) - focus_block.position()
            remove_cmd = steno_remove(current_cursor.blockNumber(), start_pos,
                                        deleted_text, backspaces_sent, stroke, current_document)
            self.undo_stack.push(remove_cmd)
            self.last_backspaces_sent = 0
            current_cursor = self.textEdit.textCursor()
            self.cursor_block = current_cursor.blockNumber()
            self.cursor_block_position = current_cursor.positionInBlock()
        if "\n" in string_sent and string_sent != "\n":
            list_segments = string_sent.splitlines(True)
            print(list_segments)
            self.undo_stack.beginMacro("Insert Group")
            for i, segment in enumerate(list_segments):
                # because this is all occurring in one stroke, only first segment gets the stroke
                if self.player.state() == QMediaPlayer.PlayingState: stroke.append(real_time)
                if self.recorder.state() == QMediaRecorder.RecordingState: stroke.append(real_time)
                if i == 0:
                    stroke = [self.stroke_time, raw_steno, segment.rstrip("\n")]
                    insert_cmd = steno_insert(self.cursor_block, self.cursor_block_position,
                                            segment.rstrip("\n"), len(segment.rstrip("\n")), stroke, current_document)
                    self.undo_stack.push(insert_cmd)
                else:
                    stroke = [self.stroke_time, "", segment.rstrip("\n")]
                    insert_cmd = steno_insert(self.cursor_block, self.cursor_block_position,
                                            segment.rstrip("\n"), len(segment.rstrip("\n")), stroke, current_document)
                    self.undo_stack.push(insert_cmd)
                if segment.endswith("\n"):
                    self.split_paragraph()
                current_cursor = self.textEdit.textCursor()
                self.cursor_block = current_cursor.blockNumber()
                self.cursor_block_position = current_cursor.positionInBlock()
            self.last_string_sent = ""
            self.undo_stack.endMacro()
        if self.last_string_sent:
            stroke = [self.stroke_time, raw_steno, string_sent]
            if self.player.state() == QMediaPlayer.PlayingState: stroke.append(real_time)
            if self.recorder.state() == QMediaRecorder.RecordingState: stroke.append(real_time)
            insert_cmd = steno_insert(self.cursor_block, self.cursor_block_position,
                                        string_sent, len(string_sent), stroke, current_document)
            self.undo_stack.push(insert_cmd)
        self.last_string_sent = ""
        self.textEdit.document().setModified(True)
        self.statusBar.clearMessage()

    def split_paragraph(self):
        current_document = self.textEdit
        current_cursor = current_document.textCursor()
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
        split_cmd = split_steno_par(self.cursor_block, self.cursor_block_position, self.config["space_placement"], self.textEdit)
        self.undo_stack.push(split_cmd)

    def merge_paragraphs(self, add_space = True):
        current_document = self.textEdit
        current_cursor = current_document.textCursor()
        self.cursor_block = current_cursor.blockNumber() - 1
        self.cursor_block_position = current_cursor.positionInBlock()
        merge_cmd = merge_steno_par(self.cursor_block, self.cursor_block_position, self.config["space_placement"], self.textEdit, add_space = add_space)
        self.undo_stack.push(merge_cmd)

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
        # log.debug(block_data.return_all())
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
        # log.debug(block_data.return_all())
        remainder, cut_steno = extract_stroke_data(block_data["strokes"], start_pos, stop_pos, copy = False)
        action_dict = {"action": "cut", "block": current_block_num, "position_in_block": start_pos, "text": selected_text,
                        "length": len(selected_text), "steno": cut_steno}
        self.undo_stack.beginMacro("Cut")
        remove_cmd = steno_remove(current_block_num, start_pos,
                                selected_text, len(selected_text), cut_steno, self.textEdit)
        self.undo_stack.push(remove_cmd)
        self.undo_stack.endMacro()
        log.debug("Cut: %s" % str(action_dict))
        # store both as an action, and for pasting
        if store:
            self.cutcopy_storage = action_dict
            log.info("Cut: action stored for pasting")
            self.statusBar.showMessage("Cut from paragraph {par_num}, from {start} to {end}".format(par_num = current_block_num, start = start_pos, end = stop_pos))

    def paste_steno(self):
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
        self.undo_stack.beginMacro("Paste")
        insert_cmd = steno_insert(current_block_num, start_pos, action_dict["text"], 
                                    len(action_dict["text"]), action_dict["steno"], self.textEdit)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()
        self.statusBar.showMessage("Paste to paragraph {par_num}, at position {start}".format(par_num = current_block_num, start = start_pos))       

    def reset_paragraph(self):
        user_choice = QMessageBox.critical(self, "Reset Paragraph", "This will clear all data from this paragraph. This cannot be undone. You will lose all history. Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if user_choice == QMessageBox.Yes:
            pass
        else:
            return
        self.undo_stack.clear()
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        current_block.setUserData(BlockUserData())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()

    def define_scan(self):
        search_result = self.untrans_search(-1)
        self.define_retroactive()

    def define_retroactive(self):
        # search_result = self.untrans_search(-1)
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        if not current_cursor.hasSelection():
            log.info("No text selected, skipping")
            self.statusBar.showMessage("Selection needed for define.")
            return
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        # end_pos is in prep for future multi-stroke untrans
        end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        start_stroke_pos = stroke_pos_at_pos(current_block.userData()["strokes"], start_pos)
        end_stroke_pos = stroke_pos_at_pos(current_block.userData()["strokes"], end_pos)
        current_cursor.setPosition(current_block.position() + start_stroke_pos[0])
        current_cursor.setPosition(current_block.position() + end_stroke_pos[1], QTextCursor.KeepAnchor)
        self.textEdit.setTextCursor(current_cursor)
        underlying_strokes = extract_stroke_data(current_block.userData()["strokes"], start_stroke_pos[0], end_stroke_pos[1], copy = True)
        underlying_steno = "/".join([stroke[1] for stroke in underlying_strokes])
        # print(underlying_steno)
        selected_untrans = current_cursor.selectedText()
        # print(selected_untrans)
        text, ok = QInputDialog().getText(self, "Retroactive Define", "Stroke: %s \nTranslation:" % underlying_steno)
        if self.config["space_placement"] == "Before Output":
            text = " " + text.strip()
        else:
            text = text.strip = " "
        # print(text)
        if ok:
            log.debug("Define: Outline %s with translation %s" % (underlying_steno, text))
            self.engine.add_translation(normalize_steno(underlying_steno, strict = True), text.strip())
            hold_replace_text = self.replace_term.text()
            hold_search_text = self.search_term.text()
            hold_search_case = self.search_case.isChecked()
            hold_search_whole = self.search_whole.isChecked()
            self.replace_term.setText(text)
            self.search_term.setText(selected_untrans)
            self.search_case.setChecked(False)
            self.search_whole.setChecked(False)
            self.replace_everything(steno = underlying_steno)
            self.replace_term.setText(hold_replace_text)
            self.search_term.setText(hold_search_text)
            self.search_case.setChecked(hold_search_case)
            self.search_whole.setChecked(hold_search_whole)
            current_cursor= self.textEdit.textCursor()
            current_cursor.movePosition(QTextCursor.End)
            self.textEdit.setTextCursor(current_cursor)

    def insert_autocomplete(self, index):
        steno = index.data(QtCore.Qt.UserRole)
        text = index.data()
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        current_cursor.select(QTextCursor.WordUnderCursor)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        start_stroke_pos = stroke_pos_at_pos(current_block.userData()["strokes"], start_pos)
        end_stroke_pos = stroke_pos_at_pos(current_block.userData()["strokes"], end_pos)
        current_cursor.setPosition(current_block.position() + start_stroke_pos[0])
        current_cursor.setPosition(current_block.position() + end_stroke_pos[1], QTextCursor.KeepAnchor)
        self.textEdit.setTextCursor(current_cursor)
        selected_text = current_cursor.selectedText()
        # print(selected_text)
        if self.config["space_placement"] == "Before Output" and selected_text.startswith(" "):
            text = " " + text
            # print(text)
        else:
            # this is unlikely as after output would not trigger autocomplete 
            text = text + " "
        autocomplete_steno = [datetime.now().isoformat("T", "milliseconds"), steno, text] 
        self.undo_stack.beginMacro("Autocomplete: %s" % text)
        remove_cmd = steno_remove(current_cursor.blockNumber(), current_cursor.anchor() - current_block.position(),
            selected_text, len(selected_text), autocomplete_steno, self.textEdit)
        self.undo_stack.push(remove_cmd)
        # add steno
        current_cursor = self.textEdit.textCursor()
        insert_cmd = steno_insert(current_cursor.blockNumber(), current_cursor.positionInBlock(), text, 
            len(text), autocomplete_steno, self.textEdit)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()

    def insert_text(self):
        text, ok = QInputDialog().getText(self, "Insert Normal Text", "Text to insert")
        if not ok:
            return
        log.info("Inserting normal text.")
        current_cursor = self.textEdit.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        self.undo_stack.beginMacro("Insert normal text")
        fake_steno = [datetime.now().isoformat("T", "milliseconds"), "", text] 
        insert_cmd = steno_insert(current_block_num, start_pos, text, 
                                    len(text), fake_steno, self.textEdit)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()       

    def mock_del(self):
        current_cursor = self.textEdit.textCursor()
        if current_cursor.hasSelection():
            self.cut_steno(store = False)
        else:
            if current_cursor.atBlockEnd():
                return
            else:
                current_cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(current_cursor)
                self.cut_steno(store = False)            
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

    def replace(self, to_next = True, steno = "", replace_term = None):
        log.info("Perform replacement.")
        if not replace_term:
            replace_term = self.replace_term.text()
        if self.textEdit.textCursor().hasSelection():
            log.info("Replace: Replace %s with %s", self.textEdit.textCursor().selectedText(), replace_term)
            self.undo_stack.beginMacro("Replace")
            current_cursor = self.textEdit.textCursor()
            current_block = current_cursor.block()
            start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
            end_pos = start_pos + len(self.textEdit.textCursor().selectedText())
            # cut_steno = extract_stroke_data(current_block.userData(), start_pos, end_pos, True)
            fake_steno = [datetime.now().isoformat("T", "milliseconds"), steno, replace_term] 
            remove_cmd = steno_remove(current_cursor.blockNumber(), start_pos, self.textEdit.textCursor().selectedText(), 
                                        len(self.textEdit.textCursor().selectedText()), fake_steno, self.textEdit)
            self.undo_stack.push(remove_cmd)    
            insert_cmd = steno_insert(current_cursor.blockNumber(), start_pos, replace_term, 
                                        len(replace_term), fake_steno, self.textEdit)
            self.undo_stack.push(insert_cmd)
            self.undo_stack.endMacro()
        if to_next:
            log.info("Moving to next match.")        
            if self.search_untrans.isChecked():
                search_status = self.untrans_search()
            elif self.search_steno.isChecked():
                search_status = self.steno_wrapped_search()
            else:
                search_status = self.text_search()
            return(search_status)

    def replace_everything(self, steno = ""):
        cursor = self.textEdit.textCursor()
        old_wrap_state = self.search_wrap.isChecked()
        if old_wrap_state:
            self.search_wrap.setChecked(False)
        old_cursor_position = cursor.block().position()        
        cursor.movePosition(QTextCursor.Start)
        self.textEdit.setTextCursor(cursor)
        search_status = True
        log.info("Replace all: starting from beginning.")
        self.undo_stack.beginMacro("Replace All")
        while search_status:
            search_status = self.search()
            if search_status is None:
                break
            self.replace(to_next = False, steno = steno)
        self.undo_stack.endMacro()
        # not the exact position but hopefully close
        log.info("Replace all: attempting to set cursor back to original position.")
        cursor.setPosition(old_cursor_position)
        self.textEdit.setTextCursor(cursor)
        self.search_wrap.setChecked(old_wrap_state)

    def spellcheck(self):
        current_cursor = self.textEdit.textCursor()
        old_cursor_position = current_cursor.block().position()
        # current_cursor.movePosition(QTextCursor.Start)
        self.textEdit.setTextCursor(current_cursor)
        while not current_cursor.atEnd():
            current_cursor.movePosition(QTextCursor.NextWord)
            current_cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
            result = self.sp_check(current_cursor.selectedText())
            if not result and current_cursor.selectedText() not in self.spell_ignore:
                self.textEdit.setTextCursor(current_cursor)
                log.debug("Spellcheck: this word %s not in dictionary." % current_cursor.selectedText())
                suggestions = [sug for sug in self.dictionary.suggest(current_cursor.selectedText())]
                self.spellcheck_result.setText(current_cursor.selectedText())
                self.spellcheck_suggestions.clear()
                self.spellcheck_suggestions.addItems(suggestions)
                break
        if current_cursor.atEnd():
            QMessageBox.information(self, "Spellcheck", "End of document.")

    def sp_ignore_all(self):
        if self.spellcheck_result.text() != "":
            self.spell_ignore.append(self.spellcheck_result.text())
            log.debug("Ignored spellcheck words: %s" % self.spell_ignore)
        self.spellcheck()

    def sp_check(self, word):
        return self.dictionary.lookup(word)

    def sp_insert_suggest(self, item = None):
        if not item:
            item = self.spellcheck_suggestions.currentItem()
        log.debug("Spellcheck correction: %s" % item.text())
        self.undo_stack.beginMacro("Spellcheck: correct to %s" % item.text())
        self.replace(to_next= False, steno = "", replace_term= item.text())
        self.undo_stack.endMacro()       

    def set_sp_dict(self, index):
        lang = self.dict_selection.itemText(index)
        log.debug("Selecting %s dictionary for spellcheck" % lang)
        dict_path = self.file_name / "spellcheck" / lang
        self.dictionary = Dictionary.from_files(str(dict_path))
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
            self.statusBar.showMessage("Opened audio file")

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
        self.actionStopRecording.setEnabled(not value)
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
            self.statusBar.showMessage("Recording audio.")
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
        selected_folder = pathlib.Path(self.file_name)  / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".txt"))
            , _("Transcript (*.txt)")
        )
        if not selected_file[0]:
            return
        contents = self.textEdit.document().toPlainText()
        file_path = pathlib.Path(selected_file[0])
        log.info("Exporting plain text to %s.", str(file_path))
        with open(file_path, "w") as f:
            f.write(contents)
            self.statusBar.showMessage("Exported in plain text format")

    def export_ascii(self):
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".txt"))
            , _("Transcript (*.txt)")
        )
        if not selected_file[0]:
            return
        self.update_config()
        block = self.textEdit.document().begin()
        doc_lines = {}
        line = -1
        while True:
            style_name = block.userData()["style"]
            block_style = {
                    "paragraphproperties": recursive_style_format(self.styles, style_name),
                    "textproperties": recursive_style_format(self.styles, style_name, prop = "textproperties")
                }
            # print(block_style)
            page_hspan = inch_to_spaces(self.config["page_width"]) - inch_to_spaces(self.config["page_left_margin"]) - inch_to_spaces(self.config["page_right_margin"])
            page_vspan = inch_to_spaces(self.config["page_height"], 6) - inch_to_spaces(self.config["page_top_margin"], 6) - inch_to_spaces(self.config["page_bottom_margin"], 6)
            if self.page_max_char.value() != 0:
                page_hspan = self.page_max_char.value()
            if self.page_max_lines.value() != 0:
                page_vspan = self.page_max_lines.value()
            # print(page_hspan)
            # print(page_vspan) 
            par_dict = format_text(block, block_style, page_hspan, line)
            doc_lines.update(par_dict)
            # print(doc_lines)
            line = line + len(par_dict)
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()
        if self.enable_line_num.isChecked():
            page_line_num = 1
            for key, line in doc_lines.items():
                if page_line_num > page_vspan:
                    page_line_num = 1
                num_line = str(page_line_num).rjust(2)
                text_line = doc_lines[key]["text"]
                doc_lines[key]["text"] = f"{num_line} {text_line}"
                page_line_num += 1
        if self.enable_timestamp.isChecked():
            for key, line in doc_lines.items():
                text_line = doc_lines[key]["text"]
                line_time = datetime.strptime(line["time"], "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')
                doc_lines[key]["text"] = f"{line_time} {text_line}"
        file_path = pathlib.Path(selected_file[0])
        with open(file_path, "w", encoding="utf-8") as f:
            for key, line in doc_lines.items():
                if key % page_vspan == 0:
                    # header
                    quotient, mod = divmod(key, page_vspan)
                    header_left = self.header_left.text().replace("%p", str(quotient + 1))
                    header_center = self.header_center.text().replace("%p", str(quotient + 1))
                    header_right = self.header_right.text().replace("%p", str(quotient + 1))
                    header_text = header_center.center(page_hspan)
                    header_text = header_left + header_text[len(header_left):]
                    header_text = header_text[:(len(header_text)-len(header_right))] + header_right
                    f.write(f"{header_text}\n")
                text_line = line["text"]
                f.write(f"{text_line}\n")
                if key % page_vspan == (page_vspan - 1):
                    quotient, mod = divmod(key, page_vspan)
                    footer_left = self.footer_left.text().replace("%p", str(quotient + 1))
                    footer_center = self.footer_center.text().replace("%p", str(quotient + 1))
                    footer_right = self.footer_right.text().replace("%p", str(quotient + 1))
                    footer_text = footer_center.center(page_hspan)
                    footer_text = footer_left + footer_text[len(footer_left):]
                    footer_text = footer_text[:(len(footer_text)-len(footer_right))] + footer_right
                    f.write(f"{footer_text}\n")

    def export_html(self):
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".html"))
            , _("Transcript (*.html)")
        )
        if not selected_file[0]:
            return
        block = self.textEdit.document().begin()
        self.update_config()
        doc_lines = {}
        line = -1
        while True:
            style_name = block.userData()["style"]
            block_style = {
                    "paragraphproperties": recursive_style_format(self.styles, style_name),
                    "textproperties": recursive_style_format(self.styles, style_name, prop = "textproperties")
                }
            page_hspan = inch_to_spaces(self.config["page_width"]) - inch_to_spaces(self.config["page_left_margin"]) - inch_to_spaces(self.config["page_right_margin"])
            page_vspan = inch_to_spaces(self.config["page_height"], 6) - inch_to_spaces(self.config["page_top_margin"], 6) - inch_to_spaces(self.config["page_bottom_margin"], 6)
            if self.page_max_char.value() != 0:
                page_hspan = self.page_max_char.value()
            if self.page_max_lines.value() != 0:
                page_vspan = self.page_max_lines.value()
            par_dict = format_text(block, block_style, page_hspan, line)
            doc_lines.update(par_dict)
            line = line + len(par_dict)
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()
        if self.enable_line_num.isChecked():
            page_line_num = 1
            for key, line in doc_lines.items():
                if page_line_num > page_vspan:
                    page_line_num = 1
                num_line = str(page_line_num).rjust(2)
                text_line = doc_lines[key]["text"]
                doc_lines[key]["text"] = f"{num_line} {text_line}"
                page_line_num += 1
        if self.enable_timestamp.isChecked():
            for key, line in doc_lines.items():
                text_line = doc_lines[key]["text"]
                line_time = datetime.strptime(line["time"], "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')
                doc_lines[key]["text"] = f"{line_time} {text_line}"
        file_path = pathlib.Path(selected_file[0])
        root = ET.Element("html")
        head = ET.SubElement(root, "head")
        body = ET.SubElement(root, "body")
        pre = ET.SubElement(body, "pre")
        for_html = []
        for k, v in doc_lines.items():
            if k % page_vspan == 0:
                # header
                quotient, mod = divmod(key, page_vspan)
                header_left = self.header_left.text().replace("%p", str(quotient + 1))
                header_center = self.header_center.text().replace("%p", str(quotient + 1))
                header_right = self.header_right.text().replace("%p", str(quotient + 1))
                header_text = header_center.center(page_hspan)
                header_text = header_left + header_text[len(header_left):]
                header_text = header_text[:(len(header_text)-len(header_right))] + header_right
                for_html.append(header_text)
            for_html.append(doc_lines[k]["text"])
            if k % page_vspan == (page_vspan - 1):
                quotient, mod = divmod(key, page_vspan)
                footer_left = self.footer_left.text().replace("%p", str(quotient + 1))
                footer_center = self.footer_center.text().replace("%p", str(quotient + 1))
                footer_right = self.footer_right.text().replace("%p", str(quotient + 1))
                footer_text = footer_center.center(page_hspan)
                footer_text = footer_left + footer_text[len(footer_left):]
                footer_text = footer_text[:(len(footer_text)-len(footer_right))] + footer_right
                for_html.append(footer_text)
        for_html_string = "\n".join(for_html)
        # print(for_html_string)
        pre.text = for_html_string
        html_string = ET.tostring(element = root, encoding = "unicode", method = "html")
        log.info("Export HTML to %s.", str(file_path))
        # print(html_string)
        with open(file_path, "w+", encoding="utf-8") as f:
            f.write(html_string)
        self.statusBar.showMessage("Exported in HTML format")

    def export_plain_ascii(self):
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".txt"))
            , _("Transcript (*.txt)")
        )
        if not selected_file[0]:
            return
        contents = self.textEdit.document().toPlainText()
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
        with open(file_path, "w", encoding="utf-8") as f:
            for line in doc_lines:
                f.write(f"{line}\n")
            self.statusBar.showMessage("Exported in ASCII format")

    def export_srt(self):
        """
        srt format: line 1: block number
                    line 2: timestamp from --> to (millisecond separator comma, not period)
                    line 3: text
                    line 4: empty
                    line 7: textstart
        """
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".srt"))
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
        with open(file_path, "w", encoding="utf-8") as f:
            for line in doc_lines:
                f.write(f"{line}\n")
            self.statusBar.showMessage("Exported in srt format")
            log.info("srt file successfully exported to %s", str(file_path))
        
    def export_odt(self):
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".odt"))
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
            page_layout_dict = {"pagewidth": "%.2fin" % self.page_width.value(), 
                                "pageheight": "%.2fin" % self.page_height.value(), "printorientation": "portrait",
                                "margintop": "%.2fin" % self.page_top_margin.value(), 
                                "marginbottom": "%.2fin" % self.page_bottom_margin.value(), 
                                "marginleft":  "%.2fin" % self.page_left_margin.value(), 
                                "marginright": "%.2fin" % self.page_right_margin.value(), "writingmode": "lr-tb"}
            if self.page_max_lines.value() != 0:
                page_layout_dict["layoutgridlines"] = str(self.page_max_lines.value())
                page_layout_dict["layoutgridmode"] = "line"
            log.debug(page_layout_dict)
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
                lineconfig_style = LinenumberingConfiguration(stylename = "Line_20_numbering", restartonpage = "true", offset = "0.15in", 
                                                                numformat = "1", numberposition = "left", increment = str(self.line_num_freq.value()))
                s.addElement(lineconfig_style)
            fonts = textdoc.fontfacedecls
            # go through every style, get all font declarations, set the fontfamily as fontname
            doc_fonts = []
            for k, v in set_styles.items():
                if v.get("textproperties"):
                    doc_fonts.append(v["textproperties"]["fontfamily"])
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
                        tab_list = style["paragraphproperties"]["tabstop"]
                        style_tab = TabStops()
                        if isinstance(tab_list, str):
                            tab_list = [tab_list]
                        for i in tab_list:
                            true_tab = TabStop(position = i)
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
            s = textdoc.styles
            master_page = textdoc.getElementsByType(MasterPage)
        frame_style = Style(name = "Frame", family = "graphic")
        frame_prop = GraphicProperties(attributes = {"verticalpos": "middle", "verticalrel": "char", "horizontalpos": "from-left", "horizontalrel": "paragraph", "opacity": "0%"})
        frame_style.addElement(frame_prop)
        s.addElement(frame_style)
        block = self.textEdit.document().begin()
        doc_lines = {}
        line = -1
        page_width = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("pagewidth")
        page_height = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("pageheight")
        page_lmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("marginleft")
        page_rmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("marginright")
        page_tmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("margintop")
        page_bmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("marginbottom")
        # print(page_width)
        # print("page_width")
        text_width = float(page_width.replace("in", "")) - float(page_lmarg.replace("in", "")) - float(page_rmarg.replace("in", ""))
        # print("text_width")
        # print(text_width)
        text_height = float(page_height.replace("in", "")) - float(page_tmarg.replace("in", "")) - float(page_bmarg.replace("in", ""))
        while True:
            style_name = block.userData()["style"]
            block_style = {
                    "paragraphproperties": recursive_style_format(self.styles, style_name),
                    "textproperties": recursive_style_format(self.styles, style_name, prop = "textproperties")
                }
            txt_format = txtprop_to_textformat(block_style["textproperties"])
            font_metrics = QFontMetrics(txt_format.font())
            # print("font char width")
            # print(font_metrics.averageCharWidth())
            # print(font_metrics.lineSpacing())
            chars_in_inch = round(1 / pixel_to_in(font_metrics.averageCharWidth()))
            height_in_inch = round(1 / pixel_to_in(font_metrics.lineSpacing()))
            page_hspan = inch_to_spaces(text_width, chars_in_inch)
            # print("page_hspan")
            # print(page_hspan)
            page_vspan = inch_to_spaces(text_height, height_in_inch)
            if self.page_max_char.value() != 0:
                # page_hspan = self.page_max_char.value()
                if page_vspan > self.page_max_char.value():
                    text_width = self.page_max_char.value() / chars_in_inch
            # print(page_hspan)
            # print(page_vspan) 
            par_dict = format_odf_text(block, block_style, chars_in_inch, text_width, line)
            doc_lines.update(par_dict)
            # print(doc_lines)
            line = line + len(par_dict)
            if not block.userData()["style"]:
                log.info("Paragraph has no style, setting to first style %s" % next(iter(set_styles)))
                par_block = P(stylename = next(iter(set_styles)))
            else:
                par_block = P(stylename = block.userData()["style"])
            # this function is important to respect \t and other whitespace properly. 
            for k, v in par_dict.items():
                # the new line causes an automatic line break
                if self.enable_timestamp.isChecked():
                    line_time = par_dict[k]["time"]
                    time_text = datetime.strptime(line_time, "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')
                    line_frame = Frame(attributes = {"stylename": "Frame", "anchortype": "char", "x": "-1.5in", "width": "0.9in"})
                    line_textbox = TextBox()
                    line_frame.addElement(line_textbox)
                    line_textbox.addElement(P(text = time_text, stylename = next(iter(set_styles))))
                    par_block.addElement(line_frame)
                line_text = par_dict[k]["text"]
                addTextToElement(par_block, line_text)
            textdoc.text.addElement(par_block)
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()
        header = Header()
        header_text = self.header_left.text() + "\t" + self.header_center.text() + "\t" + self.header_right.text()
        header_par = P(stylename = "Header_20_Footer")
        if "%p" in header_text:
            split_htext = header_text.split("%p")
            for i in split_htext:
                addTextToElement(header_par, i)
                if i != split_htext[-1]:
                    header_par.addElement(PageNumber(selectpage = "current"))
        else:
            addTextToElement(header_par, header_text)
        header.addElement(header_par)
        footer = Footer()
        footer_text = self.footer_left.text() + "\t" + self.footer_center.text() + "\t" + self.footer_right.text()
        footer_par = P(stylename = "Header_20_Footer")
        if "%p" in footer_text:
            split_ftext = footer_text.split("%p")
            for i in split_ftext:
                addTextToElement(footer_par, i)
                if i != split_ftext[-1]:
                    footer_par.addElement(PageNumber(selectpage = "current"))
        else:
            addTextToElement(footer_par, footer_text)
        footer.addElement(footer_par)
        master_page.addElement(header)
        master_page.addElement(footer)
        hf_style = Style(name = "Header_20_Footer", family = "paragraph", parentstylename = next(iter(set_styles)))
        hf_properties = ParagraphProperties(numberlines = "false")
        hf_tabstops = TabStops()
        hf_tabstops.addElement(TabStop(position = "%.2fin" % (trunc(text_width)/2)))
        hf_tabstops.addElement(TabStop(position = "%.2fin" % trunc(text_width)))
        hf_properties.addElement(hf_tabstops)
        hf_style.addElement(hf_properties)
        s.addElement(hf_style)
        textdoc.save(selected_file[0])
        self.statusBar.showMessage("Exported in OpenTextDocument format")
        # os.startfile(selected_file[0])
    # import rtf
    def import_rtf(self):
        selected_folder = pathlib.Path(self.file_name)
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Import Transcript"),
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
        self.textEdit.clear()
        self.statusBar.showMessage("Parsing RTF.")
        self.progressBar = QProgressBar(self)
        self.statusBar.addWidget(self.progressBar)
        parse_results = rtf_steno(selected_file[0], self.progressBar)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        parse_results.parse_document()
        QApplication.restoreOverrideCursor()
        style_dict, renamed_indiv_style = load_rtf_styles(parse_results)
        rtf_paragraphs = parse_results.paragraphs
        for ind, par in rtf_paragraphs.items():
            par["data"]["style"] = renamed_indiv_style[int(ind)]
        file_path = pathlib.Path(pathlib.Path(selected_file[0]).name).with_suffix(".transcript")
        file_path = self.file_name / file_path
        save_json(rtf_paragraphs, file_path)
        style_file_path = self.file_name / "styles" / pathlib.Path(pathlib.Path(selected_file[0]).name).with_suffix(".json")
        save_json(remove_empty_from_dict(style_dict), style_file_path)
        self.styles = self.load_check_styles(style_file_path)
        self.gen_style_formats()
        self.load_transcript(file_path)
        if "paperw" in parse_results.page:
            self.config["page_width"] = parse_results.page["paperw"]        
        if "paperh" in parse_results.page:
            self.config["page_height"] = parse_results.page["paperh"]
        if "margl" in parse_results.page:
            self.config["page_left_margin"] = parse_results.page["margl"]
        if "margt" in parse_results.page:
            self.config["page_top_margin"] = parse_results.page["margt"]
        if "margr" in parse_results.page:
            self.config["page_right_margin"] = parse_results.page["margr"]
        if "margb" in parse_results.page:
            self.config["page_bottom_margin"] = parse_results.page["margb"]
        self.save_config(self.file_name)
        self.setup_page()
        self.textEdit.setCursorWidth(5)
        self.textEdit.moveCursor(QTextCursor.End)
        self.style_selector.clear()
        self.style_selector.addItems([*style_dict])
        # save new page config, update page display
        self.statusBar.showMessage("Finished loading transcript data from rtf")
        log.info("Loading finished.")                

    def export_rtf(self):
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".rtf"))
            , _("RTF/CRE (*.rtf)")
        )
        if not selected_file[0]:
            return
        # automatically update config and save in case changes were not saved before
        self.update_config()
        set_styles = deepcopy(self.styles)
        font_list = []
        for k, v in set_styles.items():
            if "textproperties" in v and "fontfamily" in v["textproperties"]:
                if v["textproperties"]["fontfamily"]:
                    font_list.append(v["textproperties"]["fontfamily"])
                    v["f"] = font_list.index(v["textproperties"]["fontfamily"])
                else:
                    font_list.append(v["textproperties"]["fontfamily"])
                    v["f"] = len(font_list) - 1
        style_string = ""
        style_names = [sname for sname, data in set_styles.items()]
        for i, k in enumerate(style_names):
            set_styles[k]["styleindex"] = str(i)
        for sname, v in set_styles.items():
            if "nextstylename" in v:
                v["snext"] = str(style_names.index(v["nextstylename"]))
            if "parentstylename" in v:
                v["sbasedon"] = str(style_names.index(v["parentstylename"]))
            rtf_par_string = ""
            if "paragraphproperties" in v:
                par_dict = v["paragraphproperties"]
                if "marginleft" in par_dict:
                    rtf_par_string += write_command("li", value = in_to_twip(par_dict["marginleft"]))
                if "marginright" in par_dict:
                    rtf_par_string += write_command("ri", value = in_to_twip(par_dict["marginright"]))
                if "textindent" in par_dict:
                    rtf_par_string += write_command("fi", value = in_to_twip(par_dict["textindent"]))
                if "textalign" in par_dict:
                    if par_dict["textalign"] == "left":
                        rtf_par_string += write_command("ql")
                    if par_dict["textalign"] == "right":
                        rtf_par_string += write_command("qr")
                    if par_dict["textalign"] == "justify":
                        rtf_par_string += write_command("qj")
                    if par_dict["textalign"] == "center":
                        rtf_par_string += write_command("qc")
                if "margintop" in par_dict:
                    rtf_par_string += write_command("sb", value = in_to_twip(par_dict["margintop"]))
                if "marginbottom" in par_dict:
                    rtf_par_string += write_command("sa", value = in_to_twip(par_dict["marginbottom"]))
                if "tabstop" in par_dict:
                    if isinstance(par_dict["tabstop"], str):
                        tabstop = [par_dict["tabstop"]]
                    else:
                        tabstop = par_dict["tabstop"]
                    for i in tabstop:
                        rtf_par_string += write_command("tx", value = in_to_twip(i))
            v["rtf_par_style"] = rtf_par_string
            rtf_text_string = ""
            if "textproperties" in v:
                txt_dict = v["textproperties"]
                # remember that fonts were numbered already
                if "f" in v:
                    rtf_text_string += write_command("f", value = str(v["f"]))
                if "fontsize" in txt_dict:
                    rtf_text_string += write_command("fs", value = int(float(txt_dict["fontsize"].replace("pt", ""))) * 2)
                if "fontstyle" in txt_dict:
                    rtf_text_string += write_command("i")
                if "fontweight" in txt_dict:
                    rtf_text_string += write_command("b")
                if "textunderlinetype" in txt_dict:
                    rtf_text_string += write_command("ul")
            v["rtf_txt_style"] = rtf_text_string
        fonttbl_string = ""
        for ind, font in enumerate(font_list):
            font_string = "{" + write_command("f", value = str(ind)) +  write_command("fmodern", text = font) + ";}"
            fonttbl_string += font_string + "\n"
        stylesheet_string = ""
        for k, v in set_styles.items():
            single_style = ""
            single_style += write_command("s", value = v["styleindex"])
            if "snext" in v:
                single_style += write_command("snext", value = v["snext"])
            if "sbasedon" in v:
                single_style += write_command("sbasedon", value = v["sbasedon"])
            single_style += v["rtf_par_style"]
            stylesheet_string += "{" + single_style + " " + k + ";}\n"
        steno_string = []
        block = self.textEdit.document().begin()
        stroke_count = 0
        while True:
            steno_string.append("\n")
            steno_string.append(write_command("par"))
            steno_string.append(write_command("pard"))
            if not block.userData()["style"]:
                log.info("Paragraph has no style, setting to first style %s" % next(iter(set_styles)))
                par_style = next(iter(set_styles))
            else:
                par_style = block.userData()["style"]
            par_style_string = write_command("s", value = set_styles[par_style]["styleindex"])
            par_style_string += set_styles[par_style]["rtf_par_style"]
            par_style_string += set_styles[par_style]["rtf_txt_style"]
            steno_string.append(par_style_string)
            strokes = block.userData()["strokes"]
            stroke_count += len(strokes)
            for i in strokes:
                steno_string.append(generate_stroke_rtf(i))
            # enter style string here
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()           
        document_string = []
        document_string.append("{")
        # meta
        document_string.append(write_command("rtf", value = 1))
        document_string.append(write_command("ansi"))
        document_string.append(write_command("deff", value = 0))
        commit = return_commits(self.repo)
        last_commit = datetime.strptime(commit[-1][1], "%a %b %d %Y %H:%M:%S")
        recent_commit = datetime.strptime(commit[0][1], "%a %b %d %Y %H:%M:%S")
        commits = f'{len(commit):03}'
        document_string.append(write_command("cxrev", value = commits, visible = False, group = True))
        document_string.append(write_command("cxtranscript", visible = False, group = True))
        document_string.append(write_command("cxsystem", "Plover2CAT", visible = False, group = True))
        info_string = []
        create_string = write_command("yr", value = last_commit.year) + write_command("mo", value = last_commit.month) + write_command("dy", value = last_commit.day)
        backup_string = write_command("yr", value = recent_commit.year) + write_command("mo", value = recent_commit.month) + write_command("dy", value = recent_commit.day)
        page_vspan = inch_to_spaces(self.config["page_height"], 6) - inch_to_spaces(self.config["page_top_margin"], 6) - inch_to_spaces(self.config["page_bottom_margin"], 6)
        if self.page_max_lines.value() != 0:
            page_vspan = self.page_max_lines.value()        
        info_string.append(write_command("cxnoflines", value = page_vspan))
        # cxlinex and cxtimex is hardcoded as it is also harcoded in odf
        # based on rtf spec, confusing whether left text margin, or left page margin
        info_string.append(write_command("creatim", value = create_string))
        info_string.append(write_command("buptim", value = backup_string))
        info_string.append(write_command("cxlinex", value = int(in_to_twip(-0.15))))
        info_string.append(write_command("cxtimex", value = int(in_to_twip(-1.5))))
        info_string.append(write_command("cxnofstrokes", value = stroke_count))
        document_string.append(write_command("info", "".join(info_string), group = True))
        document_string.append(write_command("fonttbl", text = fonttbl_string, group = True))
        document_string.append(write_command("colortbl", value = ";", group = True))
        document_string.append(write_command("stylesheet", text = stylesheet_string, group = True))
        document_string.append(write_command("paperw", value = in_to_twip(self.page_width.value())))
        document_string.append(write_command("paperh", value = in_to_twip(self.page_height.value())))
        document_string.append(write_command("margl", value = in_to_twip(self.page_left_margin.value())))
        document_string.append(write_command("margr", value = in_to_twip(self.page_right_margin.value())))
        document_string.append(write_command("margt", value = in_to_twip(self.page_top_margin.value())))
        document_string.append(write_command("margb", value = in_to_twip(self.page_bottom_margin.value())))
        document_string.append("".join(steno_string))
        document_string.append("}")
        with open(selected_file[0], "w", encoding = "utf8") as f:
            f.write("".join(document_string))