import os
import subprocess
import string
import re
import pathlib
import json
import textwrap
from datetime import datetime, timezone
from collections import Counter, deque
from shutil import copyfile
from copy import deepcopy, copy
from sys import platform
from spylls.hunspell import Dictionary
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository
from dulwich import porcelain

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import (QBrush, QColor, QTextCursor, QFont, QFontMetrics, QTextDocument, 
QCursor, QStandardItem, QStandardItemModel, QPageSize, QTextBlock, QTextFormat, QTextBlockFormat, 
QTextOption, QTextCharFormat, QKeySequence, QPalette, QDesktopServices)
from PyQt5.QtWidgets import (QMainWindow, QFileDialog, QInputDialog, QListWidgetItem, QTableWidgetItem, 
QStyle, QMessageBox, QDialog, QFontDialog, QColorDialog, QUndoStack, QLabel, QMenu,
QCompleter, QApplication, QTextEdit, QPlainTextEdit, QProgressBar, QAction, QToolButton)
from PyQt5.QtMultimedia import (QMediaContent, QMediaPlayer, QMediaRecorder, 
QAudioRecorder, QMultimedia, QVideoEncoderSettings, QAudioEncoderSettings)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QFile, QTextStream, QUrl, QTime, QDateTime, QSettings, QRegExp, QSize, QStringListModel, QSizeF, QTimer, QThread
_ = lambda txt: QtCore.QCoreApplication.translate("Plover2CAT", txt)

import plover

from plover.engine import StenoEngine
from plover.steno import Stroke, normalize_steno, normalize_stroke
from plover.dictionary.base import load_dictionary
from plover.system.english_stenotype import DICTIONARIES_ROOT, ORTHOGRAPHY_WORDLIST
from plover.system import _load_wordlist
from plover import log

from . __version__ import __version__

from plover_cat.plover_cat_ui import Ui_PloverCAT
from plover_cat.fieldDialogWindow import fieldDialogWindow
from plover_cat.affixDialogWindow import affixDialogWindow
from plover_cat.shortcutDialogWindow import shortcutDialogWindow
from plover_cat.indexDialogWindow import indexDialogWindow
from plover_cat.suggestDialogWindow import suggestDialogWindow
from plover_cat.captionDialogWindow import captionDialogWindow

from plover_cat.rtf_parsing import *
from plover_cat.constants import *
from plover_cat.qcommands import *
from plover_cat.helpers import * 
from plover_cat.steno_objects import *
from plover_cat.spellcheck import *
from plover_cat.export_helpers import * 
from plover_cat.FlowLayout import FlowLayout
from plover_cat.documentWorker import documentWorker
from plover_cat.captionWorker import captionWorker

scowl = _load_wordlist(ORTHOGRAPHY_WORDLIST, DICTIONARIES_ROOT)

class PloverCATWindow(QMainWindow, Ui_PloverCAT):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        # ui and widgets setup
        self.setupUi(self)
        self.recentfileflow = FlowLayout()
        self.recentfileflow.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.recentfileflow.setObjectName("recentfileflow")
        self.flowparent.addLayout(self.recentfileflow)
        self.flowparent.addStretch()
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
        self.tabifyDockWidget(self.dockPaper, self.dockNavigation)
        self.tabifyDockWidget(self.dockAudio, self.dockStenoData)
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
        if settings.contains("backgroundcolor"):
            back_color = QColor(settings.value("backgroundcolor"))
            window_pal = self.palette()
            window_pal.setColor(QPalette.Base, back_color)
            self.setPalette(window_pal)
        if settings.contains("suggestionsource"):
            self.suggest_source.setCurrentIndex(int(settings.value("suggestionsource")))
        if settings.contains("recentfiles"):
            self.recent_file_menu()
        self.config = {}
        self.file_name = ""
        self.backup_document = {}
        self.styles = {}
        self.txt_formats = {}
        self.par_formats = {}
        self.user_field_dict = {}
        self.auto_paragraph_affixes = {}
        self.index_dialog = indexDialogWindow({})
        self.caption_dialog = captionDialogWindow() 
        self.suggest_dialog = suggestDialogWindow(None, self.engine, scowl)
        self.cap_worker = None
        self.styles_path = ""
        self.stroke_time = ""
        self.audio_file = ""
        self.cursor_block = 0
        self.cursor_block_position = 0
        self.last_raw_steno = ""
        self.last_string_sent = ""
        self.last_backspaces_sent = 0
        self.track_lengths = deque(maxlen = 10)
        self.autosave_time = QTimer()
        self.undo_stack = QUndoStack(self)
        self.actionUndo = self.undo_stack.createUndoAction(self)
        undo_icon = QtGui.QIcon()
        undo_icon.addFile(":/arrow-curve-180.png", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionUndo.setIcon(undo_icon)
        self.actionUndo.setShortcutContext(QtCore.Qt.WindowShortcut)
        self.actionUndo.setToolTip("Undo writing or other action")
        self.actionUndo.setShortcut("Ctrl+Z")
        self.actionUndo.setObjectName("actionUndo")
        self.actionRedo = self.undo_stack.createRedoAction(self)
        redo_icon = QtGui.QIcon()
        redo_icon.addFile(":/arrow-curve.png", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionRedo.setIcon(redo_icon)
        self.actionRedo.setShortcutContext(QtCore.Qt.WindowShortcut)
        self.actionRedo.setToolTip("Redo writing or other action")
        self.actionRedo.setShortcut("Ctrl+Y")
        self.actionRedo.setObjectName("actionRedo")
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionUndo)
        self.menuEdit.addAction(self.actionRedo)
        self.undoView.setStack(self.undo_stack)
        self.cutcopy_storage = deque(maxlen = 5)
        self.repo = None
        self.thread = QThread()
        self.progressBar = QProgressBar()
        self.spell_ignore = []
        self.caption_cursor_pos = 0
        self.menu_enabling()
        self.update_field_menu()
        self.update_style_menu()
        self.set_shortcuts()
        # connections:
        ## engine connections
        self.textEdit.setEnabled(True)
        engine.signal_connect("stroked", self.on_stroke) 
        engine.signal_connect("stroked", self.log_to_tape) 
        engine.signal_connect("send_string", self.on_send_string)
        engine.signal_connect("send_backspaces", self.count_backspaces)     
        ## file setting/saving
        self.actionQuit.triggered.connect(lambda: self.action_close())
        self.actionNew.triggered.connect(lambda: self.create_new())
        self.actionClose.triggered.connect(lambda: self.close_file())
        self.actionOpen.triggered.connect(lambda: self.open_file())
        self.actionSave.triggered.connect(lambda: self.save_file())
        self.actionSaveAs.triggered.connect(lambda: self.save_as_file())
        self.menuRecentFiles.triggered.connect(self.recentfile_open)
        self.actionEnableAutosave.triggered.connect(self.autosave_setup)
        self.actionSetAutosaveTime.triggered.connect(self.set_autosave_time)
        self.autosave_time.timeout.connect(self.autosave)
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
        self.actionCaptioning.triggered.connect(self.setup_captions)
        self.actionFlushCaption.triggered.connect(self.flush_caption)
        self.actionAddChangeAudioTimestamps.triggered.connect(self.modify_audiotime)
        ## editor related connections
        self.actionClearParagraph.triggered.connect(lambda: self.reset_paragraph())
        self.textEdit.complete.connect(self.insert_autocomplete)
        self.textEdit.cursorPositionChanged.connect(self.update_gui)
        self.editorCheck.stateChanged.connect(self.editor_lock)
        self.submitEdited.clicked.connect(self.edit_user_data)
        self.actionCopy.triggered.connect(lambda: self.copy_steno())
        self.actionCut.triggered.connect(lambda: self.cut_steno())
        self.actionPaste.triggered.connect(lambda: self.paste_steno())
        self.menuClipboard.triggered.connect(self.paste_steno)
        self.undo_stack.indexChanged.connect(self.check_undo_stack)
        self.actionJumpToParagraph.triggered.connect(self.jump_par)
        self.navigationList.itemDoubleClicked.connect(self.heading_navigation)
        self.textEdit.customContextMenuRequested.connect(self.context_menu)
        self.revert_version.clicked.connect(self.revert_file)
        ## insert related
        self.textEdit.send_del.connect(self.mock_del)
        self.textEdit.send_key.connect(self.mock_key)
        self.textEdit.send_bks.connect(self.mock_bks)
        self.actionInsertImage.triggered.connect(lambda: self.insert_image())
        self.actionInsertNormalText.triggered.connect(self.insert_text)
        self.actionEditFields.triggered.connect(self.edit_fields)
        self.menuField.triggered.connect(self.insert_field)
        self.reveal_steno_refresh.clicked.connect(self.refresh_steno_display)
        self.actionAutomaticAffixes.toggled.connect(self.enable_affix)
        self.actionEditAffixes.triggered.connect(self.edit_auto_affixes)
        self.menuIndexEntry.triggered.connect(lambda action, el = None: self.insert_index_entry(el = el, action = action))
        self.actionEditIndices.triggered.connect(self.edit_indices)
        self.actionRedact.triggered.connect(self.insert_redacted)     
        ## steno related edits
        self.actionMergeParagraphs.triggered.connect(lambda: self.merge_paragraphs())
        self.actionSplitParagraph.triggered.connect(lambda: self.split_paragraph())
        self.actionRetroactiveDefine.triggered.connect(lambda: self.define_retroactive())
        self.actionDefineLast.triggered.connect(lambda: self.define_scan())
        self.actionDeleteLast.triggered.connect(lambda: self.delete_scan())
        self.actionAutocompletion.triggered.connect(self.setup_completion)
        self.actionAddAutocompletionTerm.triggered.connect(self.add_autocomplete_item)
        self.actionTranslateTape.triggered.connect(self.tape_translate)
        ## dict related
        self.actionAddCustomDict.triggered.connect(lambda: self.add_dict())
        self.actionRemoveTranscriptDict.triggered.connect(lambda: self.remove_dict())
        self.actionTranscriptSuggestions.triggered.connect(lambda: self.transcript_suggest())
        ## style connections
        self.edit_page_layout.clicked.connect(self.update_config)
        self.editCurrentStyle.clicked.connect(self.style_edit)
        self.actionCreateNewStyle.triggered.connect(self.new_style)
        self.actionRefreshEditor.triggered.connect(self.refresh_editor_styles)
        self.actionStyleFileSelect.triggered.connect(self.select_style_file)
        self.actionGenerateStyleFromTemplate.triggered.connect(self.style_from_template)
        self.style_selector.activated.connect(self.update_paragraph_style)
        self.blockFont.currentFontChanged.connect(self.calculate_space_width)
        self.menuParagraphStyle.triggered.connect(self.change_style)
        # self.textEdit.ins.connect(self.change_style)
        ## view
        self.actionWindowFont.triggered.connect(lambda: self.change_window_font())
        self.actionBackgroundColor.triggered.connect(lambda: self.change_backgrounds())
        self.actionShowAllCharacters.triggered.connect(lambda: self.show_invisible_char())
        self.actionPaperTapeFont.triggered.connect(lambda: self.change_tape_font())
        ## tools
        self.actionStyling.triggered.connect(lambda: self.show_toolbox_pane(self.styling_pane))
        self.actionPageFormat.triggered.connect(lambda: self.show_toolbox_pane(self.page_format_pane))
        self.actionFindReplacePane.triggered.connect(lambda: self.show_find_replace())
        self.actionParagraph.triggered.connect(lambda: self.show_toolbox_pane(self.paragraph_pane))
        self.actionAudioRecording.triggered.connect(lambda: self.show_toolbox_pane(self.audio_recording_pane))
        self.actionSpellcheck.triggered.connect(lambda: self.show_toolbox_pane(self.spellcheck_pane))
        self.actionStenoSearch.triggered.connect(lambda: self.show_stenospell())
        self.actionSearchWikipedia.triggered.connect(lambda: self.search_online("https://en.wikipedia.org/wiki/Special:Search/{0}"))
        self.actionSearchMerriamWebster.triggered.connect(lambda: self.search_online("http://www.merriam-webster.com/dictionary/{0}"))
        self.actionSearchOED.triggered.connect(lambda: self.search_online("https://www.oed.com/search/dictionary/?scope=Entries&q={0}"))
        self.actionSearchGoogle.triggered.connect(lambda: self.search_online("https://www.google.com/search?q={0}"))
        self.actionSearchDuckDuckGo.triggered.connect(lambda: self.search_online("https://duckduckgo.com/?q={0}"))
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
        ## steno search
        self.steno_search.clicked.connect(lambda: self.spell_steno())
        ## suggestions
        self.suggest_sort.toggled.connect(lambda: self.get_suggestions())
        self.suggest_source.currentIndexChanged.connect(lambda: self.get_suggestions())
        ## tape
        self.textEdit.document().blockCountChanged.connect(lambda: self.get_suggestions())
        self.numbers = {number: letter for letter, number in plover.system.NUMBERS.items()}
        self.strokeLocate.clicked.connect(lambda: self.stroke_to_text_move())
        # export
        self.actionPlainText.triggered.connect(lambda: self.export_text())
        self.actionASCII.triggered.connect(lambda: self.export_ascii())
        self.actionPlainASCII.triggered.connect(lambda: self.export_plain_ascii())
        self.actionHTML.triggered.connect(lambda: self.export_html())
        self.actionSubRip.triggered.connect(lambda: self.export_srt())
        self.actionODT.triggered.connect(lambda: self.export_odt())
        self.actionRTF.triggered.connect(lambda: self.export_rtf())
        self.actionTape.triggered.connect(lambda: self.export_tape())
        # help
        self.actionUserManual.triggered.connect(lambda: self.open_help())
        self.actionAbout.triggered.connect(lambda: self.about())
        self.actionAcknowledgements.triggered.connect(lambda: self.acknowledge())
        self.actionEditMenuShortcuts.triggered.connect(self.edit_shortcuts)
        # status bar
        self.statusBar.showMessage("Create New Transcript or Open Existing...")
        self.cursor_status = QLabel("Par,Char: {line},{char}".format(line = 0, char = 0))
        self.cursor_status.setObjectName("cursor_status")
        self.statusBar.addPermanentWidget(self.cursor_status)
        log.debug("Main window open.")
    # menu/gui management
    def set_shortcuts(self):
        shortcut_file = pathlib.Path(plover.oslayer.config.CONFIG_DIR) / "plover2cat" / "shortcuts.json"
        if not shortcut_file.exists():
            log.debug("No shortcut file exists, using default menu shortcuts.")
            return
        else:
            with open(shortcut_file, "r") as f:
                shortcuts = json.loads(f.read())
        log.debug(f"Shortcuts: {shortcuts}")
        for identifier, keysequence in shortcuts.items():
            try:
                select_action = self.findChild(QAction, identifier)
                select_action.setShortcut(QKeySequence(keysequence)) 
            except:
                pass   

    def edit_shortcuts(self):
        shortcut_dict = {}
        menu_names = []
        action_names = []
        for act in self.findChildren(QAction):
            txt = act.text()
            name = act.objectName()
            if txt and name:
                shortcut_dict[name] = act.shortcut().toString()
                menu_names.append(txt)
                action_names.append(name)
        self.shortcut_dialog = shortcutDialogWindow(shortcut_dict, menu_names, action_names)
        res = self.shortcut_dialog.exec_()
        if res:
            shortcut_file = pathlib.Path(plover.oslayer.config.CONFIG_DIR) / "plover2cat" / "shortcuts.json"
            if not shortcut_file.exists():
                save_json({}, shortcut_file)
            with open(shortcut_file, "r") as f:
                shortcuts = json.loads(f.read())
                shortcuts.update(self.shortcut_dialog.shortcut_dict)
            save_json(remove_empty_from_dict(shortcuts), shortcut_file)
            self.set_shortcuts()
        
    def about(self):
        log.debug("User activated 'About' dialog.")
        QMessageBox.about(self, "About",
                "This is Plover2CAT version %s, a computer aided transcription plugin for Plover." % __version__)

    def acknowledge(self):
        log.debug("User activated 'Acknowledgements' dialog.")
        QMessageBox.about(self, "Acknowledgements",
                        "Plover2CAT is built on top of Plover, the open source stenotype engine. "
                        "It owes its development to the members of the Plover discord group who provided suggestions and bug finding. "
                        "PyQt5 and Plover are both licensed under the GPL. Fugue icons are by Yusuke Kamiyamane, under the Creative Commons Attribution 3.0 License.")

    def open_help(self):
        log.debug("User activated 'User Manual' link.")
        user_manual_link = QUrl("https://github.com/greenwyrt/plover2CAT/tree/main/docs")
        QtGui.QDesktopServices.openUrl(user_manual_link)

    def context_menu(self, pos):
        log.debug("User activated context menu.")
        menu = QMenu()
        menu.addAction(self.actionRetroactiveDefine)
        menu.addAction(self.actionMergeParagraphs)
        menu.addAction(self.actionSplitParagraph)
        menu.addAction(self.actionCut)
        menu.addAction(self.actionCopy)
        menu.addAction(self.actionPaste)
        menu.exec_(self.textEdit.viewport().mapToGlobal(pos))

    def menu_enabling(self, value = True):
        log.debug("Menu (dis/en)abling.")
        self.menuEdit.setEnabled(not value)
        self.menuSteno_Actions.setEnabled(not value)
        self.menuDictionary.setEnabled(not value)
        self.menuAudio.setEnabled(not value)
        self.menuStyling.setEnabled(not value)
        self.menuInsert.setEnabled(not value)
        self.menuExport_as.setEnabled(not value)
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

    def update_field_menu(self):
        log.debug("Updating field sub-menu.")
        self.menuField.clear()
        for ind, (k, v) in enumerate(self.user_field_dict.items()):
            label = "{%s}: %s" % (k, v)
            action = QAction(label, self.menuField)
            if ind < 10:           
                action.setShortcut("Ctrl+Shift+%d" % ind)
            action.setData(k)
            self.menuField.addAction(action)

    def update_style_menu(self):
        log.debug("Updating style sub-menu.")
        self.menuParagraphStyle.clear()
        for ind, name in enumerate(self.styles.keys()):
            label = name
            action = QAction(label, self.menuParagraphStyle)
            if ind < 10:
                action.setShortcut(f"Ctrl+{ind}")
            action.setData(ind)
            self.menuParagraphStyle.addAction(action)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def recent_file_menu(self):
        log.debug("Updating recent files menu.")
        self.menuRecentFiles.clear()
        self.clear_layout(self.recentfileflow)
        settings = QSettings("Plover2CAT", "OpenCAT")
        recent_file_paths = settings.value("recentfiles", [])
        for dir_path in recent_file_paths:
            transcript_path = pathlib.Path(dir_path)
            if not transcript_path.exists():
                continue
            label = transcript_path.stem
            action = QAction(label, self.menuRecentFiles)
            action.setData(dir_path)
            action.setToolTip(dir_path)
            self.menuRecentFiles.addAction(action)
            tb = QToolButton()
            icon = QtGui.QIcon()
            icon.addFile(":/document-text-large.png", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            tb.setDefaultAction(action)
            tb.setIcon(icon)
            tb.setIconSize(QSize(32, 32))
            tb.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            tb.setAutoRaise(True)
            tb.setToolTip(dir_path)
            self.recentfileflow.addWidget(tb)

    def setup_completion(self, checked):
        log.debug("Setting up autocompletion.")
        if not checked:
            self.textEdit.setCompleter(None)
            return
        self.completer = QCompleter(self)
        wordlist_path = self.file_name / "sources" / "wordlist.json"
        if not wordlist_path.exists():
            log.warning("Wordlist does not exist.")
            QMessageBox.warning(self, "Autocompletion", "The required file wordlist.json is not available in the sources folder. See user manual for format.")
            self.statusBar.showMessage("Wordlist.json for autocomplete does not exist in sources directory. Passing.")
            return
        check_return = self.engine.reverse_lookup("{#Return}")
        if not check_return:
            log.warning("Active dictionaries missing a {#Return} stroke")
            QMessageBox.warning(self, "Autocompletion", "No active dictionaries have an outline for {#Return}. One is recommended for autocompletion. See user manual.")
            self.actionAutocompletion.setChecked(False)
            return
        self.completer.setModel(self.model_from_file(str(wordlist_path)))
        self.completer.setModelSorting(QCompleter.CaseInsensitivelySortedModel)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWrapAround(False)
        self.textEdit.setCompleter(self.completer)
        self.statusBar.showMessage("Autocompletion from wordlist.json enabled.")

    def model_from_file(self, fileName):
        f = QFile(fileName)
        if not f.open(QFile.ReadOnly):
            return(QStringListModel(self.completer))
        with open(fileName, "r") as f:
            completer_dict = json.loads(f.read())
        words = QStandardItemModel(self.completer)
        log.debug("Constructing autocomplete model.")
        for key, value in completer_dict.items():
            item = QStandardItem()
            # removes any newlines/tabs, otherwise breaks autocomplete
            key = " ".join(key.split())
            item.setText(key)
            item.setData(value, QtCore.Qt.UserRole)
            words.appendRow(item)
        return(words)

    def change_window_font(self):
        font, valid = QFontDialog.getFont()
        if valid:
            self.setFont(font)
            log.debug("User set window font.")       

    def change_backgrounds(self):
        palette = self.palette()
        old_color = palette.color(QPalette.Base)
        color = QColorDialog.getColor(old_color)
        if color.isValid():
            palette = self.palette()
            palette.setColor(QPalette.Base, color)
            self.setPalette(palette)
            log.debug("User set background color.")

    def change_tape_font(self):
        font, valid = QFontDialog.getFont()
        if valid:
            self.strokeList.setFont(font)
            log.debug("User set paper tape font.")

    def show_invisible_char(self):
        doc_options = self.textEdit.document().defaultTextOption()
        if self.actionShowAllCharacters.isChecked():
            log.debug("User enabled show invisible characters.")      
            doc_options.setFlags(doc_options.flags() | QTextOption.ShowTabsAndSpaces | QTextOption.ShowLineAndParagraphSeparators)
        else:
            log.debug("User disabled show invisible characters.")      
            doc_options.setFlags(doc_options.flags() & ~QTextOption.ShowTabsAndSpaces & ~QTextOption.ShowLineAndParagraphSeparators)
        self.textEdit.document().setDefaultTextOption(doc_options)
        
    def calculate_space_width(self, font):
        new_font = font
        new_font.setPointSize(self.blockFontSize.value())
        metrics = QFontMetrics(new_font)
        space_space = metrics.averageCharWidth()
        self.fontspaceInInch.setValue(round(pixel_to_in(space_space), 2))
        log.debug("Update calculation of chararacter width for selected font.")

    def jump_par(self):
        current_cursor = self.textEdit.textCursor()
        max_blocks = self.textEdit.document().blockCount()
        current_block_num = current_cursor.blockNumber()
        block_num, ok = QInputDialog().getInt(self, "Jump to paragraph...", "Paragraph (0-based): ", current_block_num, 0, max_blocks)
        if ok:
            log.debug(f"User set jump to block {block_num}")
            self.navigate_to(block_num)

    def show_toolbox_pane(self, pane):
        if not self.dockProp.isVisible():
            self.dockProp.setVisible(True)    
        self.tabWidget.setCurrentWidget(pane)
        log.debug(f"User set {pane.objectName()} pane.")            

    def show_find_replace(self):
        if self.textEdit.textCursor().hasSelection() and self.search_text.isChecked():
            self.search_term.setText(self.textEdit.textCursor().selectedText())
        if not self.dockProp.isVisible():
            self.dockProp.setVisible(True)
        self.tabWidget.setCurrentWidget(self.find_replace_pane)
        log.debug("User set find pane visible.")

    def show_stenospell(self):
        current_cursor = self.textEdit.textCursor()
        if current_cursor.hasSelection():
            current_block = current_cursor.block()
            start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
            end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
            start_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(start_pos)
            end_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(end_pos)
            underlying_strokes = current_block.userData()["strokes"].extract_steno(start_stroke_pos[0], end_stroke_pos[1])
            underlying_steno = "/".join([element.data[0].stroke for element in underlying_strokes if element.data[0].element == "stroke"])        
            self.steno_outline.setText(underlying_steno)
        if not self.dockProp.isVisible():
            self.dockProp.setVisible(True) 
        self.tabWidget.setCurrentWidget(self.stenospell_pane)  
        log.debug("User set steno spell pane visible.")

    def search_online(self, link):
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            self.statusBar.showMessage("No text selected for online search.")
            return
        QDesktopServices.openUrl(QUrl(link.format(current_cursor.selectedText())))

    def heading_navigation(self, item):
        block_number = item.data(Qt.UserRole)
        log.debug(f"User navigating to block {block_number}.")
        self.navigate_to(block_number)

    def navigate_to(self, block_number):
        new_block = self.textEdit.document().findBlockByNumber(block_number)
        current_cursor = self.textEdit.textCursor()
        current_cursor.setPosition(new_block.position())
        self.textEdit.setTextCursor(current_cursor)
        log.debug(f"Editor cursor set to start of block {block_number}.")

    def update_gui(self):
        if not self.file_name:
            return
        self.text_to_stroke_move()
        current_cursor = self.textEdit.textCursor()
        if current_cursor.block().userData():
            self.display_block_steno(current_cursor.block().userData()["strokes"])
            self.display_block_data()
            self.update_style_display(current_cursor.block().userData()["style"])
        # skip if still on same block
        if self.cursor_block == self.textEdit.textCursor().blockNumber():
            log.debug("Cursor in same paragraph as previous.")
            return            
        # consolidate all needed updates here
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
        self.update_navigation()

    def update_navigation(self):     
        block = self.textEdit.document().begin()
        self.navigationList.clear()
        log.debug("Nagivation pane updated.")
        for i in range(self.textEdit.document().blockCount()):
            block_data = block.userData()
            if not block_data: continue
            if block_data["style"] in self.styles and "defaultoutlinelevel" in self.styles[block_data["style"]]:
                item = QListWidgetItem()
                level = int(self.styles[block_data["style"]]["defaultoutlinelevel"])
                txt = " " * level + block.text()
                item.setText(txt)
                item.setData(Qt.UserRole, block.blockNumber())
                self.navigationList.addItem(item)
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()            

    def update_index_menu(self, index_dict):
        if not index_dict:
            return
        log.debug("Updating index entry insertion sub-menu.")
        self.menuIndexEntry.clear()
        for ind, (k, v) in enumerate(index_dict.items()):
            label = "%s %s" % (k, v["prefix"])
            action = QAction(label, self.menuIndexEntry)
            action.setObjectName(f"index{ind}")
            action.setData((k, v["prefix"], v["hidden"]))
            self.menuIndexEntry.addAction(action)        

    def clipboard_menu(self):
        self.menuClipboard.clear()
        for ind, snippet in enumerate(self.cutcopy_storage):
            label = snippet.to_text()
            action = QAction(label, self.menuClipboard)
            action.setObjectName(f"clipboard{ind}")
            action.setData(ind)
            self.menuClipboard.addAction(action)

    def set_autosave_time(self):
        log.debug("User set autosave time.")
        settings = QSettings("Plover2CAT", "OpenCAT")
        if settings.contains("autosaveinterval"):
            min_save = settings.value("autosaveinterval")
        else:
            min_save = 5      
        num, ok = QInputDialog().getInt(self, "Set autosave interval.", "Minutes:", min_save, 1, 100)
        if ok:
            log.debug(f"User set autosave interval to {num}.")
            settings.setValue("autosaveinterval", num)
            if self.actionEnableAutosave.isChecked():
                self.autosave_setup(True)

    def autosave_setup(self, checked):
        settings = QSettings("Plover2CAT", "OpenCAT")
        if settings.contains("autosaveinterval"):
            min_save = settings.value("autosaveinterval")
        else:
            min_save = 5
        milli = min_save * 60 * 1000           
        if checked:
            self.autosave_time.stop()
            self.autosave_time.start(milli)
        else:
            self.autosave_time.stop()
    # open/close/save
    def create_new(self):
        self.mainTabs.setCurrentIndex(1)
        project_dir = QFileDialog.getExistingDirectory(self, "Select Directory", plover.oslayer.config.CONFIG_DIR)
        if not project_dir:
            log.debug("No directory selected, not creating transcript folder.")
            return
        if not pathlib.Path(project_dir).exists:
            user_choice = QMessageBox.question(self, "Create New", "Specified file path does not exist. Create new?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                pathlib.Path(project_dir).mkdir(parents = True)
                log.debug("Creating new transcript folder from provided path.")
            else:
                log.warning("Abort new transcript creation because path does not exist.")
                return            
        project_dir = pathlib.Path(project_dir)
        transcript_dir_name = "transcript-" + datetime.now().strftime("%Y-%m-%dT%H%M%S")
        transcript_dir_path = project_dir / transcript_dir_name
        log.debug("Project directory:" + str(transcript_dir_path))
        os.mkdir(transcript_dir_path)
        self.file_name = transcript_dir_path
        config_path = transcript_dir_path / "config.CONFIG"
        plover_engine_config = self.engine.config
        attach_space = plover_engine_config["space_placement"]
        default_config["space_placement"] = attach_space
        with open(config_path, "w") as f:
            json.dump(default_config, f)
            log.debug("Project configuration file created.")
        self.config = self.load_config_file(transcript_dir_path)
        log_dict = {"action": "config", "config": self.config}
        log.info(f"Config: {log_dict}")
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
        log.debug("Repo created.")
        self.repo = Repo.init(str(transcript_dir_path))
        self.textEdit.clear()
        self.setup_page()
        self.strokeList.clear()
        self.suggestTable.clearContents()
        self.menu_enabling(False)
        self.update_field_menu()
        self.update_style_menu()
        self.autosave_setup(self.actionEnableAutosave.isChecked())
        self.recentfile_store(str(self.file_name))
        self.mainTabs.setCurrentIndex(1)
        self.statusBar.showMessage("Created project.")
        log.debug("New project successfully created and set up.")
        self.update_paragraph_style()
        document_cursor = self.textEdit.textCursor()
        document_cursor.setBlockFormat(self.par_formats[self.style_selector.currentText()])
        document_cursor.setCharFormat(self.txt_formats[self.style_selector.currentText()]) 
        self.textEdit.setCurrentCharFormat(self.txt_formats[self.style_selector.currentText()]) 
        self.textEdit.setTextCursor(document_cursor) 
        self.textEdit.document().setDefaultFont(self.txt_formats[self.style_selector.currentText()].font())
        self.undo_stack.clear()  
        self.parent().setWindowTitle(f"Plover2CAT - {str(self.file_name.stem)}") 

    def open_file(self, file_path = ""):
        self.mainTabs.setCurrentIndex(1)
        if not file_path:
            name = "Config"
            extension = "config"
            selected_folder = QFileDialog.getOpenFileName( self, _("Open " + name), plover.oslayer.config.CONFIG_DIR, _(name + "(*." + extension + ")"))[0]
            if not selected_folder:
                log.debug("No config file was selected for loading. Aborting.")
                return
            selected_folder = pathlib.Path(selected_folder).parent
        else:
            selected_folder = pathlib.Path(file_path)
        self.statusBar.showMessage("Opening project.")
        if self.file_name != "":
            QMessageBox.warning(self, "Open File", "Existing transcript. Close before opening another.")
            return
        log.debug("Loading project files from %s", str(selected_folder))
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")
        transcript_tape = selected_folder.joinpath(selected_folder.stem).with_suffix(".tape")
        self.file_name = selected_folder
        config_contents = self.load_config_file(selected_folder)
        log_dict = {"action": "config", "config": self.config}
        log.info(f"Config: {log_dict}")
        self.config = config_contents
        self.textEdit.clear()
        self.strokeList.clear()
        self.suggestTable.clearContents()
        style_path = selected_folder / config_contents["style"]
        log.debug("Loading styles for transcript.")
        self.styles = self.load_check_styles(style_path)
        self.gen_style_formats()
        self.set_dictionary_config(config_contents["dictionaries"])
        default_spellcheck_path = selected_folder / "spellcheck"
        if default_spellcheck_path.exists():
            available_dicts = [file for file in default_spellcheck_path.iterdir() if str(file).endswith("dic")]
            for dic in available_dicts:
                self.dict_selection.addItem(text = dic.stem, userData = dic)
            # if available_dicts:
            #     self.dict_selection.addItems(available_dicts)
        spellcheck_path = pathlib.Path(plover.oslayer.config.CONFIG_DIR) / "plover2cat" / "spellcheck"
        if spellcheck_path.exists():
            available_dicts = [file for file in spellcheck_path.iterdir() if str(file).endswith("dic")]
            for dic in available_dicts:
                self.dict_selection.addItem(text = dic.stem, userData = dic)
        # self.setup_speaker_ids()
        self.strokeList.clear()
        self.suggestTable.clearContents()        
        current_cursor = self.textEdit.textCursor()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        if pathlib.Path(transcript_tape).is_file():
            log.debug("Tape file found, loading.")
            self.statusBar.showMessage("Loading tape.")
            tape_file = QFile(str(transcript_tape))
            tape_file.open(QFile.ReadOnly|QFile.Text)
            istream = QTextStream(tape_file)
            self.strokeList.document().setPlainText(istream.readAll())
            self.strokeList.verticalScrollBar().setValue(self.strokeList.verticalScrollBar().maximum())
            log.debug("Loaded tape.")
        if pathlib.Path(transcript).is_file():
            self.load_transcript(transcript)
            self.statusBar.showMessage("Finished loading transcript data.")         
        self.textEdit.setCursorWidth(5)
        self.textEdit.moveCursor(QTextCursor.End)
        self.setup_page()
        self.menu_enabling(False)
        self.update_field_menu()
        self.update_style_menu()
        present_index = self.extract_indexes()
        self.update_index_menu(present_index)
        QApplication.restoreOverrideCursor()
        export_path = selected_folder / "export"
        pathlib.Path(export_path).mkdir(parents = True, exist_ok=True)
        ## manually set first block data  
        new_block = self.textEdit.document().firstBlock()
        if not new_block.userData():
            block_dict = BlockUserData()
            block_dict["creationtime"] = datetime.now().isoformat("T", "milliseconds")
            new_block.setUserData(block_dict)
        log.debug("Project files, if exist, have been loaded.")
        try:
            self.repo = Repo(selected_folder)
            self.dulwich_save()
        except NotGitRepository:
            self.repo = Repo.init(selected_folder)
        self.recentfile_store(str(self.file_name))
        self.mainTabs.setCurrentIndex(1)         
        self.statusBar.showMessage("Setup complete. Ready for work.")
        self.autosave_setup(self.actionEnableAutosave.isChecked())
        if self.textEdit.document().characterCount() == 1:
            self.update_paragraph_style()
            document_cursor = self.textEdit.textCursor()
            document_cursor.setBlockFormat(self.par_formats[self.style_selector.currentText()])
            document_cursor.setCharFormat(self.txt_formats[self.style_selector.currentText()])  
            self.textEdit.document().setDefaultFont(self.txt_formats[self.style_selector.currentText()].font())
        self.undo_stack.clear() 
        self.parent().setWindowTitle(f"Plover2CAT - {str(self.file_name.stem)}") 

    def save_file(self):
        if not self.file_name:
            log.debug("No project dir set, cannot save file.")
            return
        selected_folder = pathlib.Path(self.file_name)
        self.update_config()
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")        
        self.save_transcript(transcript)
        if str(self.styles_path).endswith(".json"):
            save_json(self.styles, self.styles_path)
        self.textEdit.document().setModified(False)
        self.undo_stack.setClean()
        self.dulwich_save(message = "user save")
        self.statusBar.showMessage("Saved project data")  

    def save_transcript(self, path):      
        json_document = self.backup_document
        log.debug("Extracting block data for transcript save")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar.showMessage("Saving transcript data.")
        block = self.textEdit.document().begin()
        status = 0
        for i in range(self.textEdit.document().blockCount()):
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
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()      
        log.debug("Saving transcript data to %s", str(path))
        if len(json_document) > self.textEdit.document().blockCount():
            for num in range(self.textEdit.document().blockCount(), len(json_document)):
                log.debug(f"Extra paragraphs in backup document. Removing {num}.")
                json_document.pop(str(num), None)
        save_json(json_document, path)
        QApplication.restoreOverrideCursor()
        return True

    def dulwich_save(self, message = "autosave"):
        self.statusBar.showMessage("Saving versioned copy.")
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
        log.debug("Transcript file found, loading")
        self.textEdit.hide()
        with open(transcript, "r") as f:
            self.statusBar.showMessage("Reading transcript data.")
            json_document = json.loads(f.read())
        self.backup_document = deepcopy(json_document)
        self.textEdit.moveCursor(QTextCursor.Start)
        document_cursor = self.textEdit.textCursor()
        self.statusBar.showMessage("Loading transcript data.")
        self.progressBar = QProgressBar()
        self.progressBar.setMaximum(len(json_document))
        self.progressBar.setFormat("Load transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        ef = element_factory()
        ea = element_actions()
        self.textEdit.blockSignals(True)
        self.textEdit.document().blockSignals(True)
        self.textEdit.clear()
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
                self.progressBar.setValue(document_cursor.blockNumber())
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
                self.textEdit.setTextCursor(document_cursor)
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
                            self.textEdit.document().addResource(
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
                self.progressBar.setValue(document_cursor.blockNumber())
                QApplication.processEvents()
        if document_cursor.block().userData() == None:
            document_cursor.block().setUserData(BlockUserData())
        self.textEdit.document().blockSignals(False)
        self.textEdit.blockSignals(False)
        self.textEdit.show()
        self.undo_stack.clear()
        self.statusBar.removeWidget(self.progressBar)
        log.debug("Loaded transcript.")   

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
            log.debug("No directory selected, skipping save.")
            return
        selected_folder = pathlib.Path(selected_folder)
        transcript_dir_name = pathlib.Path("transcript-" + datetime.now().strftime("%Y-%m-%dT%H%M%S"))
        transcript_dir_path = selected_folder / transcript_dir_name
        os.mkdir(transcript_dir_path)
        tape_contents = self.strokeList.document().toPlainText()
        transcript = transcript_dir_path.joinpath(transcript_dir_path.stem).with_suffix(".transcript")
        transcript_tape = transcript_dir_path.joinpath(transcript_dir_path.stem).with_suffix(".tape")
        log.debug("Saving transcript to new path %s" % str(transcript_dir_path))
        self.statusBar.showMessage("Saving transcript data.")       
        transcript = selected_folder.joinpath(selected_folder.stem).with_suffix(".transcript")
        self.save_transcript(transcript)
        with open(transcript_tape, "w") as f:
            f.write(tape_contents)
            log.debug("Saving tape data to new path %s" % str(transcript_tape))
        self.file_name = transcript_dir_path
        self.setWindowTitle(str(self.file_name))
        self.textEdit.document().setModified(False)
        self.statusBar.showMessage("Saved transcript data")

    def autosave(self):
        if self.undo_stack.isClean():
            return
        transcript_dir = pathlib.Path(self.file_name)
        transcript_name = "." + str(transcript_dir.stem) + ".transcript"
        transcript = transcript_dir / transcript_name
        log.debug(f"Autosaving to {transcript}.")
        transcript = pathlib.Path(transcript)
        if transcript.exists():
            transcript.unlink()
        save_res = self.save_transcript(transcript)       
        if save_res and os.name == "nt":
            # hide file on windows systems
            hide_file(str(transcript))
            self.statusBar.showMessage("Autosave complete.")  

    def close_file(self):
        if not self.undo_stack.isClean():
            user_choice = QMessageBox.question(self, "Close", "Are you sure you want to close without saving changes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.debug("User choice to close without saving")
                pass
            else:
                log.debug("Abort project close because of unsaved changes.")
                return False
        # restore dictionaries back to original
        self.restore_dictionary_from_backup()
        if self.recorder.status() == QMediaRecorder.RecordingState:
            self.stop_record()
        ## resets textedit and vars
        self.file_name = ""
        if self.index_dialog is not None:
            self.index_dialog.close()
        self.config = {}
        self.user_field_dict = {}
        self.index_dialog = indexDialogWindow({})
        self.suggest_dialog = suggestDialogWindow(None, self.engine, scowl)
        if self.actionCaptioning.isChecked():
            self.setup_captions(False)
            self.actionCaptioning.setChecked(False)
        self.cursor_block = 0
        self.cursor_block_position = 0        
        self.menu_enabling()
        self.update_field_menu()
        self.update_style_menu()
        self.update_index_menu({})
        self.menuClipboard.clear()
        self.cutcopy_storage.clear()
        self.textEdit.clear()
        self.mainTabs.setCurrentIndex(0)
        # self.textEdit.setPlainText("Welcome to Plover2CAT\nSet up or create a transcription folder first with File->New...\nA timestamped transcript folder will be created.")        
        self.strokeList.clear()
        self.suggestTable.clearContents()
        self.undo_stack.clear()
        self.parSteno.clear()
        self.autosave_time.stop()
        self.statusBar.showMessage("Project closed")
        self.parent()._update_title()
        return True

    def action_close(self):
        log.debug("User selected quit.")
        settings = QSettings("Plover2CAT", "OpenCAT")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowstate", self.saveState())
        settings.setValue("windowfont", self.font().toString())
        settings.setValue("tapefont", self.strokeList.font().toString())
        settings.setValue("backgroundcolor", self.palette().color(QPalette.Base))
        settings.setValue("suggestionsource", self.suggest_source.currentIndex())
        log.info("Saved window settings")
        choice = self.close_file()
        if choice:
            log.debug("Closing window.")
            self.parent().close()

    def recentfile_open(self, action):
        log.debug(f"User open recent file {action.data()}")
        if self.file_name == "":
            self.open_file(action.data())
        else:
            res = self.close_file()
            if res:
                self.open_file(action.data())

    def recentfile_store(self, path):
        settings = QSettings("Plover2CAT", "OpenCAT")
        recent_file_paths = settings.value("recentfiles", [])
        try:
            recent_file_paths.remove(path)
        except ValueError:
            pass  
        recent_file_paths.insert(0, path)
        deleted = []
        for dir_path in recent_file_paths:
            if not pathlib.Path(dir_path).exists():
                deleted.append(dir_path)
        for remove_path in deleted:
            recent_file_paths.remove(remove_path)
        del recent_file_paths[10:]
        settings.setValue("recentfiles", recent_file_paths)
        self.recent_file_menu()

    def open_root(self):
        selected_folder = pathlib.Path(self.file_name)
        log.debug(f"User open file directory {str(selected_folder)}")
        if platform.startswith("win"):
            os.startfile(selected_folder)
        elif platform.startswith("linux"):
            subprocess.call(['xdg-open', selected_folder])
        elif platform.startswith("darwin"):
            subprocess.call(['open', selected_folder])
        else:
            log.warning("Unknown platform. Not opening folder directory.")
            self.textEdit.statusBar.setMessage("Unknown operating system. Not opening file directory.")
    # dict related
    def create_default_dict(self):
        selected_folder = self.file_name
        dict_dir = selected_folder / "dict"
        dict_file_name = "default.json"
        dict_file_name = dict_dir / dict_file_name
        log.debug(f"Creating default dictionary in {str(dict_file_name)}")
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
        log.debug(f"Selected dictionary at {str(selected_file)} to add.")
        dict_dir_path = self.file_name / "dict"
        try:
            os.mkdir(dict_dir_path)
        except FileExistsError:
            pass
        dict_dir_name = dict_dir_path / selected_file.name
        if selected_file != dict_dir_name:
            log.debug(f"Copying dictionary at {str(selected_file)} to {str(dict_dir_name)}")
            copyfile(selected_file, dict_dir_name)
        list_dicts = self.engine.config["dictionaries"]
        # do not add if already in dict
        if str(selected_file) in list_dicts:
            log.debug("Selected dictionary is already in loaded dictionaries, passing.")
            return
        new_dict_config = add_custom_dicts([str(selected_file)], list_dicts)
        self.engine.config = {'dictionaries': new_dict_config}
        # update config
        config_contents = self.config
        dictionary_list = config_contents["dictionaries"]
        log.debug(f"Loaded dictionary objects: {dictionary_list}")
        dictionary_list.append(str(dict_dir_name.relative_to(self.file_name)))
        config_contents["dictionaries"] = dictionary_list
        log.debug(f"Add {str(dict_dir_name.relative_to(self.file_name))} to config")
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
        log.debug("Selected dictionary at %s to remove.", str(selected_file))
        config_contents = self.config
        dictionary_list = config_contents["dictionaries"]
        list_dicts = self.engine.config["dictionaries"]
        list_dicts = [i.path for i in list_dicts if pathlib.Path(i.path)  != selected_file]
        new_dict_config = add_custom_dicts(list_dicts, [])
        self.engine.config = {'dictionaries': new_dict_config}
        if str(selected_file.relative_to(self.file_name)) in dictionary_list:
            dictionary_list = [i for i in dictionary_list if i != str(selected_file.relative_to(self.file_name))]
            log.debug("Remove %s from config", str(selected_file.relative_to(self.file_name)))
            config_contents["dictionaries"] = dictionary_list
            self.config = config_contents
            self.update_config()
        else:
            log.debug("Selected dictionary not a transcript dictionary, passing.")

    def set_dictionary_config(self, dictionaries = None):
        # dictionaries must be passed in as list, or bad things happen
        # these dictionaries should have the relative paths to root folder
        log.debug("Setting and loading dictionar(ies)")
        plover_config = self.engine.config
        list_dicts = plover_config["dictionaries"]
        default_dict_path = self.file_name / "dict" / "default.json"
        if not default_dict_path.exists():
            log.debug("Default dict does not exist. Creating default.")
            self.create_default_dict()
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
        editor_dict_path = pathlib.Path(plover.oslayer.config.CONFIG_DIR) / "plover2cat" / "dict"
        if editor_dict_path.exists():
            available_dicts = [file for file in editor_dict_path.iterdir() if str(file).endswith("json")]
            for dic in available_dicts:
                full_paths.append(str(dic))
        new_dict_config = add_custom_dicts(full_paths, list_dicts)
        self.engine.config = {'dictionaries': new_dict_config}
        config_dict = self.config
        config_dict["dictionaries"] = list(set(config_dict["dictionaries"] + dictionaries))
        self.update_config()

    def restore_dictionary_from_backup(self):
        selected_folder = pathlib.Path(self.file_name)
        log.debug("Attempting to restore dictionaries configuration from backup.")
        backup_dictionary_location = selected_folder / "dict" / "dictionaries_backup"
        log.debug(f"Backup file location: {str(backup_dictionary_location)}")
        if backup_dictionary_location.exists():
            restored_dicts = load_dictionary_stack_from_backup(backup_dictionary_location)
            self.engine.config = {'dictionaries': restored_dicts}
            log.debug("Dictionaries restored from backup file.")

    def transcript_suggest(self):
        log.debug("User activate transcript suggestions.")
        if not self.suggest_dialog:
            self.suggest_dialog = suggestDialogWindow(None, self.engine, scowl)
        self.suggest_dialog.update_text(self.textEdit.toPlainText())
        self.suggest_dialog.show()      
        self.suggest_dialog.activateWindow()        
    # config related
    def load_config_file(self, dir_path):
        config_path = pathlib.Path(dir_path) / "config.CONFIG"
        log.debug(f"Loading configuration file from {str(config_path)}")
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
        if "user_field_dict" in config_contents:
            self.user_field_dict = config_contents["user_field_dict"]
        else:
            config_contents["user_field_dict"] = user_field_dict
            self.user_field_dict = user_field_dict
        if "auto_paragraph_affixes" in config_contents:
            self.auto_paragraph_affixes = config_contents["auto_paragraph_affixes"]
        if "enable_automatic_affix" in config_contents and config_contents["enable_automatic_affix"]:
            self.actionAutomaticAffixes.setChecked(True)
        else:
            self.actionAutomaticAffixes.setChecked(False)
        log.debug("Configuration successfully loaded.")
        return config_contents

    def save_config(self, dir_path):
        config_path = pathlib.Path(dir_path) / "config.CONFIG"
        log.debug(f"Saving config to {str(config_path)}")
        config_contents = self.config
        style_path = pathlib.Path(self.styles_path)
        config_contents["style"] = str(style_path.relative_to(self.file_name))
        with open(config_path, "w") as f:
            json.dump(config_contents, f)
            log.debug("Config saved.")
            self.statusBar.showMessage("Saved config data")

    def update_config(self):
        log.debug("User update config.")
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
        config_contents["user_field_dict"] = self.user_field_dict
        config_contents["enable_automatic_affix"] = True if self.actionAutomaticAffixes.isChecked() else False
        config_contents["auto_paragraph_affixes"] = self.auto_paragraph_affixes
        self.config = config_contents
        log_dict = {"action": "config", "config": self.config}
        log.info(f"Config: {log_dict}")
        self.save_config(self.file_name)
        self.setup_page()
    # style related
    def setup_page(self):
        doc = self.textEdit.document()
        width = float(self.config["page_width"])
        height = float(self.config["page_height"])
        log.debug(f"Setting editor page size to {str(width)}in and {str(height)}in (WxH).")
        width_pt = int(in_to_pt(width))
        height_pt = int(in_to_pt(height))
        self.textEdit.setLineWrapMode(QTextEdit.FixedPixelWidth)
        self.textEdit.setLineWrapColumnOrWidth(width_pt)
        page_size = QPageSize(QSizeF(width, height), QPageSize.Inch, matchPolicy = QPageSize.FuzzyMatch) 
        doc.setPageSize(page_size.size(QPageSize.Point))

    def create_default_styles(self):
        log.debug("Create default styles for project")
        selected_folder = self.file_name
        style_dir = selected_folder / "styles"
        style_file_name = "default.json"
        style_file_name = style_dir / style_file_name
        save_json(default_styles, style_file_name)
        log.debug(f"Default styles set in {str(style_file_name)}")

    def load_check_styles(self, path):
        path = pathlib.Path(path)
        if not path.exists():
            # go to default if the config style doesn't exist
            log.debug("Supplied config style file does not exist. Loading default.")
            path = self.file_name / "styles" / "default.json"
            if not path.exists():
                # if default somehow got deleted
                self.create_default_styles()
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
                if not sub_keys.issubset(acceptable_keys):
                    log.warning("Some first-level keys in style json are not valid.")
                    log.debug(f"First-level keys: {sub_keys}")
                    self.statusBar.showMessage("Style file failed to parse.")
                    return False
        # clear old styles out before loading from new styles
        self.style_selector.clear()
        self.style_selector.addItems([*json_styles])
        self.statusBar.showMessage("Loaded style data.")
        log.debug("Styles loaded.")
        original_style_path = path
        new_style_path = self.file_name / "styles" / original_style_path.name
        if original_style_path != new_style_path:
            log.debug(f"Copying style file at {original_style_path} to {new_style_path}")
            copyfile(original_style_path, new_style_path)
        self.styles_path = new_style_path
        self.style_file_path.setText(path.name)
        self.update_config()
        return json_styles

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

    def select_style_file(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Style JSON or odt"),
            str(self.file_name), _("Style (*.json *.odt)"))[0]
        if not selected_file:
            return
        log.debug(f"User selected style file at {selected_file}.")
        self.styles = self.load_check_styles(selected_file)
        self.gen_style_formats()

    def style_from_template(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Style ODT or RTF/CRE file"),
            str(self.file_name), _("Style template file (*.odt *.rtf)"))[0]
        if not selected_file:
            return  
        log.debug(f"User selected style template {selected_file}")
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

    def display_block_data(self):
        current_cursor = self.textEdit.textCursor()
        block_number = current_cursor.blockNumber()
        block_data = current_cursor.block().userData()
        log.debug(f"Update GUI to display block {block_number} data")
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
        self.textEdit.showPossibilities()

    def display_block_steno(self, strokes):
        # clear of last block data
        self.parSteno.clear()
        log.debug("Update reveal steno display.")
        for ind, el in enumerate(strokes.data):
            item = QListWidgetItem()
            item.setText(el.to_text())
            item.setData(Qt.ToolTipRole, el.to_display())
            item.setData(Qt.UserRole, ind)
            self.parSteno.addItem(item)     

    def refresh_steno_display(self):
        log.debug("User refresh reveal steno display")
        current_cursor = self.textEdit.textCursor()
        block_strokes = current_cursor.block().userData()["strokes"]
        self.display_block_steno(block_strokes)

    def update_paragraph_style(self):
        current_cursor = self.textEdit.textCursor()
        log.debug(f"User changed style for paragraph {current_cursor.blockNumber()}.")
        style_cmd = set_par_style(current_cursor.blockNumber(), self.style_selector.currentText(), self.textEdit, self.par_formats, self.txt_formats)
        self.undo_stack.push(style_cmd)
        self.update_style_display(self.style_selector.currentText())

    def update_style_display(self, style):
        log.debug(f"Updating style GUI for style {style}.")
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
        self.blockParentStyle.clear()
        self.blockParentStyle.addItems([*self.styles])
        if "defaultoutlinelevel" in self.styles[style]:
            self.blockHeadingLevel.setCurrentText(self.styles[style]["defaultoutlinelevel"])
        else:
            self.blockHeadingLevel.setCurrentIndex(0)
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
        log.debug(f"Editing style {style_name}.")
        new_style_dict = {"family": "paragraph"}
        if self.blockParentStyle.currentIndex() != -1:
            # this is important so a style is not based on itself
            if self.blockParentStyle.currentText() != style_name:
                new_style_dict["parentstylename"] = self.blockParentStyle.currentText()
            else:
                QMessageBox.warning(self, "Edit style", "Style cannot be parent of itself.")
                return
        if self.blockNextStyle.currentIndex() != -1:
            new_style_dict["nextstylename"] = self.blockNextStyle.currentText()
        if self.blockHeadingLevel.currentText() != "":
            new_style_dict["defaultoutlinelevel"] = self.blockHeadingLevel.currentText()
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
        min_txt_style = {}
        for k, v in new_txt_dict.items():
            if k in original_style_txt and v == original_style_txt[k]:
                continue
            else:
                min_txt_style[k] = v
        min_par_style = {}
        for k, v in new_par_dict.items():
            if k in original_style_par and v == original_style_par[k]:
                continue
            else:
                min_par_style[k] = v
        # original_style_txt.update(new_txt_dict)
        # original_style_txt = remove_empty_from_dict(original_style_txt)
        # original_style_par.update(new_par_dict)
        new_style_dict["paragraphproperties"] = min_par_style
        new_style_dict["textproperties"] = min_txt_style
        style_cmd = style_update(self.styles, style_name, new_style_dict)
        self.undo_stack.push(style_cmd)
        # self.refresh_editor_styles()

    def check_undo_stack(self, index):
        if self.undo_stack.undoText().startswith("Style:") or self.undo_stack.redoText().startswith("Style:"):
            self.refresh_editor_styles()

    def new_style(self):
        log.debug("User create new style")
        text, ok = QInputDialog().getText(self, "Create New Style", "Style Name (based on %s)" % self.style_selector.currentText(), inputMethodHints  = Qt.ImhLatinOnly)
        if not ok:
            log.debug("User cancelled style creation")
            return
        log.debug(f"Creating new style with name {text.strip()}")
        self.styles[text.strip()] = {"family": "paragraph", "parentstylename": self.style_selector.currentText()}
        self.gen_style_formats()
        if str(self.styles_path).endswith(".json"):
            save_json(self.styles, self.styles_path)
        old_style = self.style_selector.currentText()
        self.style_selector.clear()
        self.style_selector.addItems([*self.styles])
        self.style_selector.setCurrentText(old_style)
        self.update_style_menu()

    def refresh_editor_styles(self):
        if self.textEdit.document().blockCount() > 200:
            user_choice = QMessageBox.question(self, "Refresh styles", f"There are {self.textEdit.document().blockCount()} paragraphs. Style refreshing may take some time. Continue?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.No:
                return
        self.gen_style_formats()
        block = self.textEdit.document().begin()
        current_cursor = self.textEdit.textCursor()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(self.textEdit.document().blockCount())
        self.progressBar.setFormat("Re-style paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        for i in range(self.textEdit.document().blockCount()):
            try:
                block_style = block.userData()["style"]
            except TypeError:
                # block_style = ""
                continue                          
            current_cursor.setPosition(block.position())
            current_cursor.movePosition(QTextCursor.StartOfBlock)
            current_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            current_cursor.setBlockFormat(self.par_formats[block_style])
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and not frag.charFormat().isImageFormat():
                    current_cursor.setPosition(frag.position())
                    current_cursor.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                    current_cursor.setCharFormat(self.txt_formats[block_style])
                it += 1
            self.progressBar.setValue(block.blockNumber())
            QApplication.processEvents()
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()
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
        self.style_selector.setCurrentText(new_style)
        style_cmd = set_par_style(current_cursor.blockNumber(), self.style_selector.currentText(), self.textEdit, self.par_formats, self.txt_formats)
        self.undo_stack.push(style_cmd)
        self.statusBar.showMessage("Paragraph style set to {style}".format(style = new_style))

    def change_style(self, action):
        ind = action.data()
        log.debug("User shortcut to change style.")
        self.style_selector.setCurrentIndex(ind)
        current_cursor = self.textEdit.textCursor()
        style_cmd = set_par_style(current_cursor.blockNumber(), self.style_selector.currentText(), self.textEdit, self.par_formats, self.txt_formats)
        self.undo_stack.push(style_cmd)

    def editor_lock(self):
        if self.editorCheck.isChecked():
            self.submitEdited.setEnabled(False)
        else:
            self.submitEdited.setEnabled(True)

    def edit_user_data(self):
        log.debug("User edited block data.")
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
        log.debug(f"Updating block data for {self.cursor_block}.")
        # log.debug(block_data.return_all())
        self.textEdit.document().findBlockByNumber(self.cursor_block).setUserData(block_data)
        self.statusBar.showMessage("Updated paragraph {par_num} data".format(par_num = self.cursor_block))
    # engine hooked functions
    def on_send_string(self, string):
        log.debug(f"Plover engine sent string: {string}")
        self.last_string_sent = string

    def count_backspaces(self, backspace):
        log.debug(f"Plover engine sent {backspace} backspace(s)")
        self.last_backspaces_sent = backspace

    def log_to_tape(self, stroke):
        # need file to output to
        if not self.file_name:
            return
        if not self.engine.output and self.engine._machine_params.type == "Keyboard":
            return
        # if window inactive, and not capturing everything, and not enabled, don't do anything
        # print(self.textEdit.isActiveWindow())
        if not self.textEdit.isActiveWindow() and not self.actionCaptureAllOutput.isChecked():
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
        if self.player.state() == QMediaPlayer.PlayingState or self.player.state() == QMediaPlayer.PausedState:
            real_time = self.player.position() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        if self.recorder.state() == QMediaRecorder.RecordingState:
            real_time = self.recorder.duration() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        log_string = "{0}|{1}|({2},{3})\t|{4}|".format(self.stroke_time, audio_time, self.cursor_block, self.cursor_block_position, steno)
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
        log.debug("Trying to load tapey tape from default location.")
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
        '''Now parses default clippy output based on color codes.'''
        config_dir = pathlib.Path(plover.oslayer.config.CONFIG_DIR)
        clippy_location = config_dir.joinpath('clippy_2.org')
        log.debug("Trying to load clippy from default location")
        if not clippy_location.exists():
            # log.debug("Clippy load failed")
            return
        raw_lines = [line for line in open(clippy_location)]
        stroke_search = []
        for line in raw_lines:
            search_hit = clippy_strokes.search(line)
            if search_hit:
                stroke_search.append(search_hit.group(1).split(", "))
        first_stroke_search = [x[0] for x in stroke_search]
        combined_stroke_search = dict(zip(first_stroke_search, stroke_search))
        log.debug("stroke_search = " + str(stroke_search))
        if self.suggest_sort.isChecked():
            most_common_strokes = [word for word, word_count in reversed(Counter(first_stroke_search).items()) if word_count > 2]
            most_common_strokes = most_common_strokes[:min(11, len(most_common_strokes) + 1)]
        else:
            most_common_strokes = [word for word, word_count in Counter(first_stroke_search).most_common(10) if word_count > 2]
        log.debug("most_common_strokes = " + str(most_common_strokes))
        words = [self.engine.lookup(tuple(stroke.split("/"))).strip() for stroke in most_common_strokes]
        log.debug("words = " + str(words))
        self.suggestTable.clearContents()
        self.suggestTable.setRowCount(len(words))
        self.suggestTable.setColumnCount(2)
        for row in range(len(words)):
            self.suggestTable.setItem(row, 0, QTableWidgetItem(words[row]))
            self.suggestTable.setItem(row, 1, QTableWidgetItem(", ".join(combined_stroke_search[most_common_strokes[row]])))
        self.suggestTable.resizeColumnsToContents()

    def get_suggestions(self):
        if self.suggest_source.currentText() == "tapey-tape":
            self.get_tapey_tape()
        elif self.suggest_source.currentText() == "clippy_2":
            self.get_clippy()
        else:
            log.debug("Unknown suggestion source %s!" % self.suggest_source.currentText())

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
            log.debug("Move text cursor to tape position.")
        except:
            pass
        self.textEdit.blockSignals(False)

    def text_to_stroke_move(self):
        stroke_cursor = self.strokeList.textCursor()
        edit_cursor = self.textEdit.textCursor()
        edit_block = edit_cursor.block()
        block_data = edit_block.userData()
        self.strokeList.blockSignals(True)
        stroke_text = self.strokeList.document().toPlainText().split("\n")
        pos = edit_cursor.positionInBlock()
        log.debug("Move to tape line based on text cursor position.")
        self.cursor_status.setText("Par,Char: {line},{char}".format(line = edit_cursor.blockNumber(), char = pos)) 
        try:
            if edit_cursor.atBlockStart():
                stroke_time = block_data["strokes"].data[0].time
            elif edit_cursor.atBlockEnd():
                stroke_time = block_data["strokes"].data[-1].time
            else:
                stroke_data = block_data["strokes"].extract_steno(pos, pos + 1)
                stroke_time = stroke_data.data[0].time
            # no idea how fast this will be with many many more lines, probably slow
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
    def enable_affix(self, check):
        log.debug("Toggle automatic paragraph affixes.")
        self.config["enable_automatic_affix"] = check
        
    def edit_auto_affixes(self):
        log.debug("User edit paragraph affixes.")
        if not self.auto_paragraph_affixes:
            log.debug("No pre-existing affix dict.")
        self.affix_dialog = affixDialogWindow(self.auto_paragraph_affixes, [*self.styles])
        res = self.affix_dialog.exec_()
        if res == QDialog.Accepted:
            log.debug("Updating paragraph affixes.")
            self.auto_paragraph_affixes = self.affix_dialog.affix_dict

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
        paper_format, ok = QInputDialog.getItem(self, "Translate Tape", "Format of tape file:", ["Plover2CAT", "Plover (raw)", "Plover (paper)"], editable = False)
        log.debug(f"Translating tape from {selected_file} with {paper_format} format.") 
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
        if not self.file_name:
            return
        if not self.engine.output:
            return
        # do nothing if window not in focus
        if not self.textEdit.isActiveWindow() and not self.actionCaptureAllOutput.isChecked():
            return
        # case if stroke only sends commands
        if not self.last_string_sent and self.last_backspaces_sent == 0:
            return
        current_document = self.textEdit
        current_cursor = current_document.textCursor()
        if self.actionCursorAtEnd.isChecked():
            current_cursor.movePosition(QTextCursor.End)
            self.textEdit.setTextCursor(current_cursor)
        self.display_captions()
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
        self.stroke_time = datetime.now().isoformat("T", "milliseconds")
        string_sent = self.last_string_sent
        backspaces_sent = self.last_backspaces_sent
        # to deal with cases of "corrections", ie pick --> picnic, or willow --> WillowTree
        # if stem word completely removed, the stroke is removed, getting "dropped"
        if self.last_string_sent and self.last_backspaces_sent > 0 and self.track_lengths[-1] > 0 and backspaces_sent >= self.track_lengths[-1]:
            self.last_raw_steno = self.last_raw_steno + "/" + stroke_pressed.rtfcre
        else:
            self.last_raw_steno = stroke_pressed.rtfcre
        raw_steno = self.last_raw_steno
        if self.player.state() == QMediaPlayer.PlayingState or self.player.state() == QMediaPlayer.PausedState:
            real_time = self.player.position() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        elif self.recorder.state() == QMediaRecorder.RecordingState:
            real_time = self.recorder.duration() - self.audioDelay.value()
            audio_time = ms_to_hours(real_time)
        focus_block = self.textEdit.document().findBlockByNumber(self.cursor_block)
        if len(focus_block.text()) == 0 and not string_sent and backspaces_sent > 0:
            # if this is first block, nothing happens since backspace erases nothing
            if focus_block == self.textEdit.document().firstBlock():
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
            strokes_data = element_collection()
        if not block_dict["audiostarttime"]:
            if self.player.state() == QMediaPlayer.PlayingState or self.player.state() == QMediaPlayer.PausedState:
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = audio_time)
            if self.recorder.state() == QMediaRecorder.RecordingState:
                block_dict = update_user_data(block_dict, key = "audiostarttime", value = audio_time)
        block_dict["strokes"] = strokes_data
        focus_block.setUserData(block_dict)
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
                    self.textEdit.setTextCursor(current_cursor)
                    self.cut_steno(store=False)
                    holding_space = -1 * start_pos
                    log.debug("%d spaces left" % holding_space)
                    self.merge_paragraphs(add_space = False)
                    # the merge is technically one "backspace"
                    holding_space -= 1
                    current_cursor = self.textEdit.textCursor()
                    cursor_pos = current_cursor.positionInBlock()
                    current_strokes = current_cursor.block().userData()["strokes"]
                    start_pos = backtrack_coord(current_cursor.positionInBlock(), holding_space, current_strokes.lens(), current_strokes.lengths())
                    log.debug(f"New starting position: {start_pos}.")
                current_cursor.setPosition(current_cursor.block().position() + start_pos, QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(current_cursor)
                self.cut_steno(store=False)
            else:
                end_pos = current_cursor.position() - focus_block.position()
                start_pos = backtrack_coord(end_pos, backspaces_sent, focus_block.userData()["strokes"].lens(), focus_block.userData()["strokes"].lengths())
                remove_cmd = steno_remove(current_document, current_cursor.blockNumber(), start_pos, end_pos - start_pos)
                self.undo_stack.push(remove_cmd)
            self.last_backspaces_sent = 0
            self.undo_stack.endMacro()
            current_cursor = self.textEdit.textCursor()
            self.cursor_block = current_cursor.blockNumber()
            self.cursor_block_position = current_cursor.positionInBlock()        
        if "\n" in string_sent and self.last_string_sent != "\n":
            list_segments = string_sent.splitlines(True)
            self.track_lengths.append(len(self.last_string_sent))
            self.undo_stack.beginMacro(f"Insert: {string_sent}")
            for i, segment in enumerate(list_segments):
                stroke = stroke_text(time = self.stroke_time, stroke = self.last_raw_steno, text = segment.rstrip("\n"))
                # because this is all occurring in one stroke, only first segment gets the stroke
                if i == 0:
                    self.last_raw_steno = ""
                if self.player.state() == QMediaPlayer.PlayingState or self.player.state() == QMediaPlayer.PausedState: 
                    stroke.audiotime = real_time
                if self.recorder.state() == QMediaRecorder.RecordingState: 
                    stroke.audiotime = real_time
                if len(stroke) != 0:
                    insert_cmd = steno_insert(current_document, self.cursor_block, self.cursor_block_position, stroke)
                    self.undo_stack.push(insert_cmd)
                if (i != (len(list_segments) - 1)) or (len(list_segments) == 1) or segment == "\n":
                    self.split_paragraph(remove_space = False)
                current_cursor = self.textEdit.textCursor()
                # update cursor position for next loop
                self.cursor_block = current_cursor.blockNumber()
                self.cursor_block_position = current_cursor.positionInBlock()
                self.to_next_style()
            self.last_string_sent = ""
            self.undo_stack.endMacro()
            return 
        if self.last_string_sent:
            self.track_lengths.append(len(self.last_string_sent))
            stroke = stroke_text(stroke = raw_steno, text = string_sent)
            if self.player.state() == QMediaPlayer.PlayingState or self.player.state() == QMediaPlayer.PausedState: 
                stroke.audiotime = real_time
            if self.recorder.state() == QMediaRecorder.RecordingState:
                stroke.audiotime = real_time
            if self.config["enable_automatic_affix"]:
                if self.last_string_sent == "\n":
                    stroke = self.add_end_auto_affix(stroke, block_dict["style"])
                if block_dict["strokes"].element_count() == 0:
                    stroke = self.add_begin_auto_affix(stroke, block_dict["style"])
            if not current_cursor.atBlockEnd() and self.last_string_sent == "\n":
                self.split_paragraph()
            else:
                insert_cmd = steno_insert(current_document, self.cursor_block, self.cursor_block_position,
                                            stroke)
                self.undo_stack.push(insert_cmd)
            self.last_string_sent = ""
        self.textEdit.document().setModified(True)
        self.statusBar.clearMessage()

    def split_paragraph(self, remove_space = True):
        current_document = self.textEdit
        current_cursor = current_document.textCursor()
        self.cursor_block = current_cursor.blockNumber()
        self.cursor_block_position = current_cursor.positionInBlock()
        new_line_stroke = stroke_text(stroke = "R-R", text = "\n")
        if self.config["enable_automatic_affix"]:
            new_line_stroke = self.add_end_auto_affix(new_line_stroke, current_cursor.block().userData()["style"])
        split_cmd = split_steno_par(self.textEdit, self.cursor_block, self.cursor_block_position, self.config["space_placement"], new_line_stroke, remove_space)
        self.undo_stack.push(split_cmd)

    def merge_paragraphs(self, add_space = True):
        current_document = self.textEdit
        current_cursor = current_document.textCursor()
        self.cursor_block = current_cursor.blockNumber() - 1
        self.cursor_block_position = current_cursor.positionInBlock()
        merge_cmd = merge_steno_par(self.textEdit, self.cursor_block, self.cursor_block_position, self.config["space_placement"], add_space = add_space)
        self.undo_stack.push(merge_cmd)

    def copy_steno(self):
        log.debug("Performing copying.")
        current_cursor = self.textEdit.textCursor()
        print(current_cursor.block().userData()["strokes"].merge_elements())
        if not current_cursor.hasSelection():
            log.debug("No text selected for copying, skipping")
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
        self.cutcopy_storage.appendleft(block_data["strokes"].extract_steno(start_pos, stop_pos))
        self.clipboard_menu()
        self.textEdit.moveCursor(QTextCursor.End)
        log.debug("Copy data stored for pasting")
        # self.statusBar.showMessage(f"Copied from paragraph {current_block_num}, from {start_pos} to {stop_pos}.")
        # restore cursor back to original position
        self.textEdit.setTextCursor(current_cursor)
        current_cursor.movePosition(current_block.position() + start_pos)
        current_cursor.movePosition(current_block.position() + stop_pos, QTextCursor.KeepAnchor)

    def cut_steno(self, store = True):
        log.debug("Perform cutting.")
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            log.debug("No text selected, skipping")
            self.statusBar.showMessage("Select text for cutting.")
            return
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        # get coordinates of selection in block
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        stop_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        log.debug(f"Cut: Cut in paragraph {current_block_num} from {start_pos} to {stop_pos}.")
        selected_text = current_cursor.selectedText()
        if re.search("\u2029", selected_text):
            # maybe one day in the far future
            self.statusBar.showMessage("Cutting across paragraphs is not supported")
            return
        block_data = current_block.userData()
        if store:
            self.cutcopy_storage.appendleft(block_data["strokes"].extract_steno(start_pos, stop_pos))
            self.clipboard_menu()
            log.debug("Data stored for pasting")
            self.statusBar.showMessage("Cut from paragraph {par_num}, from {start} to {end}".format(par_num = current_block_num, start = start_pos, end = stop_pos))
        self.undo_stack.beginMacro(f"Cut: {selected_text}")
        remove_cmd = steno_remove(self.textEdit, current_block_num, 
                            start_pos, len(selected_text))
        self.undo_stack.push(remove_cmd)
        self.undo_stack.endMacro()
        log.debug(f"Cut: Cut in paragraph {current_block_num} from {start_pos} to {stop_pos}.")

    def paste_steno(self, action = None):
        log.debug("Performing pasting.")
        index = 0
        if action:
            index = action.data()
        store_data = deepcopy(self.cutcopy_storage[index])
        if store_data == "":
            log.debug("Nothing in storage to paste, skipping")
            self.statusBar.showMessage("Cut or copy text to paste")
            return
        ea = element_actions()
        current_cursor = self.textEdit.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        self.undo_stack.beginMacro(f"Paste: {store_data.to_text()}")
        self.textEdit.blockSignals(True)
        for el in store_data.data:
            current_block = self.textEdit.textCursor().blockNumber()
            current_pos = self.textEdit.textCursor().positionInBlock()
            cmd = ea.make_action(self.textEdit, current_block, current_pos, el)
            self.undo_stack.push(cmd)
        self.textEdit.blockSignals(False)
        self.undo_stack.endMacro()
        self.statusBar.showMessage(f"Pasting to paragraph {current_block_num} at position {start_pos}.")  
        log.debug(f"Pasting to paragraph {current_block_num} at position {start_pos}.")

    def reset_paragraph(self):
        user_choice = QMessageBox.critical(self, "Reset Paragraph", "This will clear all data from this paragraph. This cannot be undone. You will lose all history. Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if user_choice != QMessageBox.Yes:
            return
        log.debug("User trigger paragraph reset.")
        self.undo_stack.clear()
        log.debug("History cleared.")
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        current_block.setUserData(BlockUserData())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()

    def insert_image(self):
        log.debug("Selecting image file for insertion")
        selected_file = QFileDialog.getOpenFileName(self, _("Select Image"), str(self.file_name), 
                            _("Image Files(*.png *.jpg *jpeg)"))[0]
        if not selected_file:
            log.debug("No image selected. Aborting")
            return
        log.debug("User selected image file: %s" % selected_file)
        selected_file = pathlib.Path(selected_file)
        asset_dir_path = self.file_name / "assets"
        log.debug("Create asset directory if not present.")
        try:
            os.mkdir(asset_dir_path)
        except FileExistsError:
            pass
        asset_dir_name = asset_dir_path / selected_file.name
        if selected_file != asset_dir_name:
            log.debug(f"Copying image at {str(selected_file)} to {str(asset_dir_name)}")
            copyfile(selected_file, asset_dir_name)
        im_element = image_text(path = asset_dir_name.as_posix())
        insert_cmd = image_insert(self.textEdit, self.textEdit.textCursor().blockNumber(), 
                        self.textEdit.textCursor().positionInBlock(), im_element)
        self.undo_stack.push(insert_cmd)

    def insert_field(self, action):
        name = action.data()
        log.debug(f"User trigger field insert {name}.")
        el = text_field(name = name, user_dict = self.user_field_dict)
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.blockNumber()
        start_pos = current_cursor.positionInBlock()
        insert_cmd = steno_insert(self.textEdit, current_block, start_pos, el)
        self.undo_stack.push(insert_cmd)

    def define_retroactive(self):
        log.debug("Define retroactive.")
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        if not current_cursor.hasSelection():
            log.debug("No text selected, skipping")
            self.statusBar.showMessage("Selection needed for define.")
            return
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        # end_pos is in prep for future multi-stroke untrans
        end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        start_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(start_pos)
        end_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(end_pos)
        current_cursor.setPosition(current_block.position() + start_stroke_pos[0])
        current_cursor.setPosition(current_block.position() + end_stroke_pos[1], QTextCursor.KeepAnchor)
        self.textEdit.setTextCursor(current_cursor)
        underlying_strokes = current_block.userData()["strokes"].extract_steno(start_stroke_pos[0], end_stroke_pos[1])
        underlying_steno = "/".join([element.data[0].stroke for element in underlying_strokes if element.data[0].element == "stroke"])
        selected_untrans = current_cursor.selectedText()
        text, ok = QInputDialog().getText(self, "Retroactive Define", "Stroke: %s \nTranslation:" % underlying_steno)
        if self.config["space_placement"] == "Before Output":
            text = " " + text.strip()
        else:
            text = text.strip() + " "
        if ok:
            log.debug(f"Define: Outline {underlying_steno} with translation {text}.")
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
            current_cursor = self.textEdit.textCursor()
            current_cursor.movePosition(QTextCursor.End)
            self.textEdit.setTextCursor(current_cursor)

    def define_scan(self):
        log.debug("Scan to redefine.")
        search_result = self.untrans_search(-1)
        self.define_retroactive()

    def delete_scan(self):
        log.debug("Scan to delete.")
        search_result = self.untrans_search(-1)
        if not search_result:
            return
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        current_block_num = current_block.blockNumber()
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        stop_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        remove_cmd = steno_remove(self.textEdit, current_block_num, 
                            start_pos, stop_pos - start_pos)  
        self.undo_stack.push(remove_cmd)      

    def add_autocomplete_item(self):
        log.debug("Add term to autocomplete.")
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            self.statusBar.showMessage("No text selected for autocomplete")
            return
        current_block = current_cursor.block()
        selected_text = current_cursor.selectedText()        
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        # end_pos has a one char deletion since otherwise it will include unwanted next stroke
        end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position() - 1
        start_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(start_pos)
        end_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(end_pos)
        underlying_strokes = current_block.userData()["strokes"].extract_steno(start_stroke_pos[0], end_stroke_pos[1])
        underlying_steno = "/".join([element.data[0].stroke for element in underlying_strokes if element.data[0].element == "stroke"])
        text, ok = QInputDialog().getText(self, "Add Autocomplete Term", "Text: %s \nSteno:" % selected_text, text = underlying_steno)
        if not ok:
            return
        wordlist_path = self.file_name / "sources" / "wordlist.json"
        if wordlist_path.exists():
            with open(wordlist_path, "r") as f:
                completer_dict = json.loads(f.read())
        else:
            completer_dict = {}
        completer_dict[selected_text.strip()] = text
        save_json(completer_dict, wordlist_path)
        log.debug(f"Adding term {text} to autocompletion.")
        self.setup_completion(self.actionAutocompletion.isChecked())

    def insert_autocomplete(self, index):
        steno = index.data(QtCore.Qt.UserRole)
        text = index.data()
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        current_cursor.select(QTextCursor.WordUnderCursor)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        end_pos = max(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        log.debug(f"Autocomplete: autocomplete word {text} from {start_pos} to {end_pos}.")
        start_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(start_pos)
        end_stroke_pos = current_block.userData()["strokes"].stroke_pos_at_pos(end_pos)
        current_cursor.setPosition(current_block.position() + start_stroke_pos[0])
        current_cursor.setPosition(current_block.position() + end_stroke_pos[1], QTextCursor.KeepAnchor)
        self.textEdit.setTextCursor(current_cursor)
        selected_text = current_cursor.selectedText()
        # print(selected_text)
        if self.config["space_placement"] == "Before Output" and selected_text.startswith(" "):
            text = " " + text
        else:
            # this is unlikely as after output would not trigger autocomplete 
            text = text + " "
        autocomplete_steno = stroke_text(stroke = steno, text = text)
        self.undo_stack.beginMacro("Autocomplete: %s" % text)
        remove_cmd = steno_remove(self.textEdit, current_cursor.blockNumber(), 
                        current_cursor.anchor() - current_block.position(), len(selected_text))
        self.undo_stack.push(remove_cmd)
        current_cursor = self.textEdit.textCursor()
        insert_cmd = steno_insert(self.textEdit, current_cursor.blockNumber(), 
                        current_cursor.positionInBlock(), autocomplete_steno)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()

    def mock_key(self, text):
        if self.engine.output:
            return
        if not self.file_name:
            return            
        if len(text) > 0:
            self.insert_text(text)
    
    def mock_bks(self):
        if self.engine.output:
            return
        if not self.file_name:
            return            
        current_cursor = self.textEdit.textCursor()
        if current_cursor.atBlockStart():
            return
        current_cursor.movePosition(QTextCursor.PreviousCharacter)
        self.textEdit.setTextCursor(current_cursor)
        self.mock_del()

    def insert_text(self, text = None):
        log.debug("User insert normal text.")
        if not text:
            text, ok = QInputDialog().getText(self, "Insert Normal Text", "Text to insert")
            if not ok:
                return
        log.debug(f"Inserting normal text {text}.")
        current_cursor = self.textEdit.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        self.undo_stack.beginMacro(f"Insert: {text}")
        fake_steno = text_element(text = text)
        insert_cmd = steno_insert(self.textEdit, current_block_num, start_pos, fake_steno)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()      

    def mock_del(self):
        if not self.file_name:
            return        
        current_cursor = self.textEdit.textCursor()
        if current_cursor.hasSelection():
            self.cut_steno(store = False)
        else:
            if current_cursor.atBlockEnd():
                return
            else:
                block_strokes = current_cursor.block().userData()["strokes"]
                # "delete" means removing one head, so has to "reverse" to get start pos
                start_pos = backtrack_coord(current_cursor.positionInBlock() + 1, 1, block_strokes.lens(), block_strokes.lengths())
                current_cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor)
                current_cursor.setPosition(current_cursor.block().position() + start_pos, QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(current_cursor)
                self.cut_steno(store = False)            

    def edit_fields(self):
        log.debug("User editing fields.")
        self.field_dialog = fieldDialogWindow(self.user_field_dict)
        # self.field_dialog.setModal(True)
        res = self.field_dialog.exec_()
        if res == QDialog.Accepted:
            log.debug("Field editor closed.")
            new_field_dict = self.field_dialog.user_field_dict
            # after user_field_dict is set, then refresh
            current_cursor = self.textEdit.textCursor()
            update_cmd = update_field(self.textEdit, current_cursor.blockNumber(), current_cursor.positionInBlock(), self.user_field_dict, new_field_dict)
            self.undo_stack.push(update_cmd)
            self.update_field_menu()

    def insert_redacted(self, text = None):
        log.debug("User insert redact text.")
        if not text:
            text, ok = QInputDialog().getText(self, "Insert Redacted Text", "Text to insert")
            if not ok:
                return
        log.debug(f"Inserting redacted text {text}.")
        current_cursor = self.textEdit.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        # todo
        # redact_steno = redact_text()

    def add_begin_auto_affix(self, element, style):
        if style not in self.auto_paragraph_affixes:
            log.debug("No prefix set for this paragraph style.")
            return(element)
        auto_el = automatic_text(prefix = self.auto_paragraph_affixes[style]["prefix"])  
        auto_el.from_dict(element.to_json())
        auto_el.element = "automatic"
        return(auto_el)                    

    def add_end_auto_affix(self, element, style):
        if style not in self.auto_paragraph_affixes:
            log.debug("No suffix set for this paragraph style.")
            return(element)
        auto_el = automatic_text(prefix = self.auto_paragraph_affixes[style]["suffix"])  
        auto_el.from_dict(element.to_json())
        auto_el.element = "automatic"
        return(auto_el)    

    def insert_index_entry(self, el = None, action = None):
        current_cursor = self.textEdit.textCursor()
        if el is None:
            index_name = action.data()[0]
            index_prefix = action.data()[1]
            index_hidden = action.data()[2]
            if current_cursor.hasSelection():
                txt = current_cursor.selectedText()
                ok = True
            else:
                txt, ok = QInputDialog.getText(self, f"Quick insert index {index_name}", f"{index_prefix}")
            if not ok:
                return
            el = index_text(prefix = index_prefix, indexname = index_name, hidden = index_hidden, text = txt)
        start_pos = current_cursor.positionInBlock()
        current_block = current_cursor.blockNumber()
        self.undo_stack.beginMacro("Insert: index entry")
        if current_cursor.hasSelection() and el == None:
            self.cut_steno(store = False)
            self.textEdit.setTextCursor(current_cursor)
            start_pos = current_cursor.positionInBlock()
        else:
            current_cursor.setPosition(min(current_cursor.position(), current_cursor.anchor()))
            start_pos = current_cursor.positionInBlock()
        insert_cmd = steno_insert(self.textEdit, current_block, start_pos, el)
        self.undo_stack.push(insert_cmd)
        self.undo_stack.endMacro()
        # present_index = self.extract_indexes()
        if not self.index_dialog:
            self.index_dialog = indexDialogWindow({})
        present_index = self.extract_indexes()
        if present_index:
            self.index_dialog.update_dict(present_index)

    def extract_indexes(self):
        index_dict = {}
        current_cursor = self.textEdit.textCursor()
        block = self.textEdit.document().begin()
        if len(self.textEdit.toPlainText()) == 0:
            return
        for i in range(self.textEdit.document().blockCount()):
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
            if block == self.textEdit.document().lastBlock():
                break
            block = block.next()
        return(index_dict)          

    def update_indices(self):
        log.debug("Updating indexes in editor.")
        present_index = self.extract_indexes()
        new_index = self.index_dialog.index_dict
        if not present_index:
            return
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.blockNumber()
        start_pos = current_cursor.positionInBlock()            
        update_cmd = update_entries(self.textEdit, current_block, start_pos, present_index, new_index)
        self.undo_stack.push(update_cmd)
        self.update_index_menu(self.index_dialog.index_dict)
    
    def edit_indices(self, show_dialog = True):
        log.debug("User editing indices.")
        if not self.index_dialog:
            self.index_dialog = indexDialogWindow({})
        present_index = self.extract_indexes()
        if present_index:
            self.index_dialog.update_dict(present_index)
        self.index_dialog.show()
        self.index_dialog.index_insert.connect(self.insert_index_entry)
        self.index_dialog.updated_dict.connect(self.update_indices)
        self.index_dialog.activateWindow()
    # search functions
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
        log.debug("Performing text search with term %s, flags %s.", search, flags)
        found = self.textEdit.document().find(search, cursor, flags)
        if not found.isNull():
            log.debug("Search success.")
            self.textEdit.setTextCursor(found)
            self.statusBar.showMessage("Match found")
            return True
        elif self.search_wrap.isChecked():
            log.debug("Search failure. Wrapping.")
            if direction == 1:
                cursor.movePosition(QTextCursor.Start)
            else:
                cursor.movePosition(QTextCursor.End)
            found = self.textEdit.document().find(search, cursor, flags)
            if not found.isNull():
                log.debug("Search success.")
                self.textEdit.setTextCursor(found)
                self.statusBar.showMessage("Wrapped search. Match found.")
                return True
            else:
                log.debug("Search failure.")
                self.statusBar.showMessage("Wrapped search. No match found.")
                return None
        else:
            log.debug("Search failure.")
            self.statusBar.showMessage("No match found.")
            return None

    def steno_wrapped_search(self, direction = 1):
        log.debug("Steno search.")
        found = self.steno_search(direction = direction)
        if not found and self.search_wrap.isChecked():
            log.debug("Wrap steno search.")
            cursor = self.textEdit.textCursor()
            if direction == -1:
                log.debug("Search starting from end.")
                cursor.movePosition(QTextCursor.End)
            else:
                log.debug("Search starting from top.")
                cursor.movePosition(QTextCursor.Start)
            self.textEdit.setTextCursor(cursor)
            found = self.steno_search(direction = direction)
        return(found)

    def steno_search(self, direction = 1):
        cursor = self.textEdit.textCursor()
        steno = self.search_term.text()
        log.debug("Searching for stroke %s in stroke data.", steno)
        if direction == -1:
            current_block = cursor.block()
            if cursor.hasSelection():
                start_pos = min(cursor.position(), cursor.anchor())
                cursor.setPosition(start_pos)
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor)
            self.textEdit.setTextCursor(cursor)
            cursor_pos = cursor.positionInBlock()
            stroke_data = current_block.userData()["strokes"].extract_steno(0, cursor_pos)
            while True:
                check_match = stroke_data.search_strokes(steno)
                if check_match is not None:
                    break
                if current_block == self.textEdit.document().firstBlock():
                    # end search after searching first block
                    check_match = None
                    break
                current_block = current_block.previous()
                stroke_data = current_block.userData()["strokes"] 
            if check_match is not None:
                block_pos = current_block.position()
                cursor.setPosition(block_pos + check_match[0])
                cursor.setPosition(block_pos + check_match[1], QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(cursor)
                log.debug("Search success.")
                self.statusBar.showMessage("Steno match found.")
                return True
            else:
                log.debug("Search failure.")
                self.statusBar.showMessage("No steno match found.")
                return None                                                                            
        else:
            current_block = cursor.block()
            if cursor.hasSelection():
                start_pos = max(cursor.position(), cursor.anchor())
                cursor.setPosition(start_pos + 1)
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor)
            self.textEdit.setTextCursor(cursor)
            cursor_pos = cursor.positionInBlock()
            stroke_data = current_block.userData()["strokes"].extract_steno(0, cursor_pos)
            while True:
                # this is different from loop above since there is an offset 
                # so cursor pos below has to add the offset
                check_match = stroke_data.search_strokes(steno)
                if check_match is not None:
                    break
                if current_block == self.textEdit.document().lastBlock():
                    # end search after searching last block
                    check_match = None
                    break
                current_block = current_block.next()
                stroke_data = current_block.userData()["strokes"] 
                cursor_pos = 0
            if check_match is not None:
                block_pos = current_block.position()               
                cursor.setPosition(block_pos + cursor_pos + check_match[0])
                cursor.setPosition(block_pos + cursor_pos + check_match[1], QTextCursor.KeepAnchor)
                self.textEdit.setTextCursor(cursor)
                log.debug("Search success.")
                self.statusBar.showMessage("Steno match found.")
                return True
            else:
                log.debug("Search failure.")
                self.statusBar.showMessage("No steno match found.")
                return None

    def untrans_search(self, direction = 1):
        flags = QTextDocument.FindFlags()
        untrans_reg = QRegExp("(\\b|\\*)(?=[STKPWHRAO*EUFBLGDZ]{3,})S?T?K?P?W?H?R?A?O?\*?E?U?F?R?P?B?L?G?T?S?D?Z?\\b")
        if direction == -1:
            flags |= QTextDocument.FindBackward
        cursor = self.textEdit.textCursor()
        found = self.textEdit.document().find(untrans_reg, cursor, flags)
        log.debug("Search for untranslated steno.")
        if not found.isNull():
            self.textEdit.setTextCursor(found)
            log.debug("Search success.")
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
                log.debug("Wrapped. Search success.")
                self.statusBar.showMessage("Wrapped search. Untrans found.")
                return True
            else:
                log.debug("Wrapped. Search failure.")
                self.statusBar.showMessage("Wrapped search. No untrans found.")
                return None
        else:
            log.debug("Search failure.")
            self.statusBar.showMessage("No untrans found.") 
            return None      

    def search_text_options(self):
        if self.search_text.isChecked():
            log.debug("Set options for text search.")
            self.search_case.setEnabled(True)
            self.search_whole.setChecked(False)
            self.search_term.setEnabled(True)
            self.search_whole.setEnabled(True)

    def search_steno_options(self):
        if self.search_steno.isChecked():
            log.debug("Set options for steno search.")
            self.search_case.setEnabled(False)
            self.search_whole.setChecked(True)
            self.search_term.setEnabled(True)
            self.search_whole.setEnabled(False)

    def search_untrans_options(self):
        if self.search_untrans.isChecked():
            log.debug("Set options for untrans search.")
            self.search_term.setEnabled(False)
            self.search_case.setEnabled(False)
            self.search_whole.setChecked(False)
            self.search_whole.setEnabled(False)           

    def replace(self, to_next = True, steno = "", replace_term = None):
        log.debug("Perform replacement.")
        if not replace_term:
            replace_term = self.replace_term.text()
        if self.textEdit.textCursor().hasSelection():
            log.debug("Replace %s with %s", self.textEdit.textCursor().selectedText(), replace_term)
            self.undo_stack.beginMacro(f"Replace: {self.textEdit.textCursor().selectedText()} with {replace_term}")
            current_cursor = self.textEdit.textCursor()
            current_block = current_cursor.block()
            start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
            fake_steno = stroke_text(stroke = steno, text = replace_term)
            remove_cmd = steno_remove(self.textEdit, current_cursor.blockNumber(), start_pos, 
                            len(self.textEdit.textCursor().selectedText()))
            self.undo_stack.push(remove_cmd)    
            insert_cmd = steno_insert(self.textEdit, current_cursor.blockNumber(), start_pos, fake_steno)
            self.undo_stack.push(insert_cmd)
            self.undo_stack.endMacro()
        if to_next:
            log.debug("Moving to next match.")        
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
        log.debug("Replace all, starting from beginning.")
        self.undo_stack.beginMacro("Replace All")
        while search_status:
            search_status = self.search()
            if search_status is None:
                break
            self.replace(to_next = False, steno = steno)
        self.undo_stack.endMacro()
        # not the exact position but hopefully close
        log.debug("Attempting to set cursor back to original position after replacements.")
        cursor.setPosition(old_cursor_position)
        self.textEdit.setTextCursor(cursor)
        self.search_wrap.setChecked(old_wrap_state)

    def sp_check(self, word):
        return self.dictionary.lookup(word)

    def spellcheck(self):
        log.debug("Perform spellcheck.")
        current_cursor = self.textEdit.textCursor()
        old_cursor_position = current_cursor.block().position()
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
        dict_path = self.dict_selection.itemData(index)
        self.dictionary = Dictionary.from_files(str(dict_path))

    def spell_steno(self):
        outline = self.steno_outline.text()
        pos = multi_gen_alternative(outline)
        res = get_sorted_suggestions(pos, self.engine)
        self.stenospell_res.clear()
        for candidate in res:
            self.stenospell_res.addItem(candidate[0])
    # audio functions
    def open_audio(self):
        if not self.file_name:
            log.debug("No audio file selected, skipping.")
            return
        audio_file = QFileDialog.getOpenFileName(self, _("Select Audio/Video File"), str(self.file_name), "Audio/Video Files (*.mp3 *.ogg *.wav *.mp4 *.mov *.wmv *.avi)")
        if audio_file[0]:
            self.audio_file = pathlib.Path(audio_file[0])
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(self.audio_file))))
            log.debug(f"Player set to selected audio {str(audio_file[0])}.")
            label_text = "Audio:" + str(self.audio_file.name)
            self.audio_label.setText(label_text)
            self.statusBar.showMessage("Opened audio file")

    def set_up_video(self, avail):
        if avail:
            log.debug("Video available for file.")
            self.viewer = QMainWindow()
            self.video = QVideoWidget()
            self.player.setVideoOutput(self.video)
            self.viewer.setWindowFlags(self.viewer.windowFlags() | Qt.WindowStaysOnTopHint)
            self.viewer.setCentralWidget(self.video)
            log.debug("Showing video widget.")
            self.video.updateGeometry()
            self.video.adjustSize()
            self.viewer.show()
        else:
            # self.viewer.hide()
            pass

    def show_hide_video(self):
        if self.viewer.isVisible():
            log.debug("Hide video.")
            self.viewer.hide()
        else:
            log.debug("Show video.")
            self.viewer.show()

    def play_pause(self):
        log.debug("User press playing/pausing audio.")
        if self.recorder.state() == QMediaRecorder.StoppedState:
            pass
        else:
            log.debug("Recording ongoing, passing.")
            self.statusBar.showMessage("Recording in progress.")
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            log.debug("Paused audio.")
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
            log.debug("Playing audio.")
            self.statusBar.showMessage("Restarted audio")
            
    def stop_play(self):
        log.debug("User press stop audio.")
        block_dict = self.textEdit.document().findBlockByNumber(self.cursor_block).userData()
        real_time = self.player.position() - self.audioDelay.value()
        block_dict = update_user_data(block_dict, key = "audioendtime", value = ms_to_hours(real_time))
        log.debug("Adding audio timestamp to data, %s", block_dict.return_all())
        self.textEdit.document().findBlockByNumber(self.cursor_block).setUserData(block_dict)
        self.player.stop()
        log.debug("Audio stopped.")
        self.statusBar.showMessage("Stopped audio")

    def update_duration(self, duration):
        self.audio_seeker.setMaximum(duration)
        self.audio_duration.setText(ms_to_hours(duration))

    def update_seeker_track(self, position):
        self.audio_seeker.setValue(position)
        self.audio_curr_pos.setText(ms_to_hours(position))

    def set_position(self, position):
        self.player.setPosition(position)
        log.debug("User set audio track to %s", ms_to_hours(position))

    def seek_position(self, direction = 1):
        log.debug("User skip ahead/behind audio.")
        seek_time = self.player.position() + direction * 5000
        self.player.setPosition(seek_time)

    def update_playback_rate(self, rate):
        log.debug("User set audio playback rate.")
        self.player.setPlaybackRate(rate)

    def record_controls_enable(self, value = True):
        log.debug("(Dis/en)able recording GUI.")
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
        self.statusBar.showMessage(self.recorder.errorString())

    def record_or_pause(self):
        if self.player.state() != QMediaPlayer.StoppedState:
            log.debug("Audio playing, passing.")
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
            log.debug("Audio settings:\nAudio Input: %s\nCodec: %s\nMIME Type: %s\nSample Rate: %s\nChannels: %s\nQuality: %s\nBitrate: %s\nEncoding:%s",
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
                    log.debug("User choice to record over existing audio file.")
                    pass
                else:
                    log.debug("Abort recording attempt.")
                    return
            self.recorder.setOutputLocation(QUrl.fromLocalFile(str(audio_file_path)))
            log.debug("Recording to %s", str(audio_file_path))
            self.statusBar.showMessage("Recording audio.")
            self.recorder.record()
        else:
            log.debug("Pausing recording.")
            self.statusBar.showMessage("Pausing recording.")
            self.recorder.pause()
    
    def stop_record(self):
        self.recorder.stop()
        log.debug("Stop recording.")
        self.record_controls_enable(True)

    def update_record_time(self):
        msg = "Recorded %s" % ms_to_hours(self.recorder.duration())
        self.statusBar.showMessage(msg)

    def setup_caption_window(self, display_font, max_blocks):
        self.caption_window = QMainWindow()
        self.caption_window.setMinimumSize(50, 50)
        self.caption_window.setWindowFlags(self.caption_window.windowFlags() | Qt.WindowStaysOnTopHint)
        self.caption_window.setWindowFlags(self.caption_window.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        self.caption_window.setWindowFlags(self.caption_window.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        self.caption_window.setWindowTitle("Plover2CAT Captions")
        self.caption_edit = QPlainTextEdit()
        self.caption_edit.setReadOnly(True)
        self.caption_edit.setCursorWidth(5)
        self.caption_edit.moveCursor(QTextCursor.End)
        self.caption_edit.ensureCursorVisible()
        # use same font for tape and caption
        self.caption_edit.document().setDefaultFont(display_font)
        if max_blocks != 0:
            self.caption_edit.document().setMaximumBlockCount(max_blocks)
        self.caption_window.setCentralWidget(self.caption_edit)
        self.caption_window.show()

    def add_cap(self, cap):
        self.caption_edit.setPlainText(cap)
        self.caption_edit.ensureCursorVisible()

    def setup_captions(self, checked):
        if checked:
            res = self.caption_dialog.exec_()
            # need to always keep cursor at end, so can undo from end, but never from middle
            self.actionCursorAtEnd.setChecked(True)
            if res:
                self.setup_caption_window(self.caption_dialog.font, self.caption_dialog.maxDisplayLines.value())
                # if captions are enabled in middle of document, don't start from beginning
                self.caption_cursor_pos = self.textEdit.textCursor().position()
                self.thread = QThread()
                self.cap_worker = captionWorker(max_length = self.caption_dialog.capLength.value(), max_lines = self.caption_dialog.maxDisplayLines.value(),
                                    remote = self.caption_dialog.remoteCapHost.currentText(), endpoint = self.caption_dialog.hostURL.text(), 
                                    port = self.caption_dialog.serverPort.text(), password = self.caption_dialog.serverPassword.text())
                self.cap_worker.moveToThread(self.thread)
                self.thread.started.connect(self.cap_worker.make_caps)
                self.cap_worker.finished.connect(self.thread.quit)
                self.cap_worker.finished.connect(self.cap_worker.deleteLater)
                # self.thread.finished.connect(self.thread.deleteLater)
                self.cap_worker.capSend.connect(self.add_cap)
                self.cap_worker.postMessage.connect(self.statusBar.showMessage)
                self.thread.start()
            else:
                self.actionCaptioning.setChecked(False)
        else:
            # do cleanup
            self.cap_worker.clean_and_stop()
            self.caption_edit.clear()
            self.caption_window.hide()

    def display_captions(self):
        if not self.actionCaptioning.isChecked():
            return
        current_cursor = self.textEdit.textCursor()
        current_cursor.movePosition(QTextCursor.PreviousWord, QTextCursor.MoveAnchor, self.caption_dialog.charOffset.value())
        new_pos = current_cursor.position()
        if self.caption_cursor_pos >= new_pos:
            return
        current_cursor.setPosition(self.caption_cursor_pos, QTextCursor.KeepAnchor)
        new_text = current_cursor.selectedText()
        self.caption_cursor_pos = new_pos
        self.cap_worker.intake(new_text)

    def flush_caption(self):
        old_pos = self.caption_cursor_pos
        current_cursor = self.textEdit.textCursor()
        current_cursor.setPosition(old_pos) 
        current_cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        new_text = current_cursor.selectedText()
        if new_text == "":
            self.cap_worker.intake("\n" + "\u2029")
        else:
            self.cap_worker.intake(new_text)
        self.caption_cursor_pos = max(current_cursor.position(), current_cursor.anchor())

    def modify_audiotime(self):
        block = self.textEdit.document().begin()
        times = []
        for i in range(self.textEdit.document().blockCount()):
            if block.userData():
                times.append(block.userData["creationtime"])
                block_time = block.userData()["strokes"].collection_time()
                times.append(block_time)
            if block == self.textEdit.document().lastBlock():
                break                
            block = block.next()
        earliest =  min([t for t in times if t])
        print(earliest)
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
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return
        contents = self.textEdit.document().toPlainText()
        file_path = pathlib.Path(selected_file[0])
        log.debug("Exporting plain text to %s.", str(file_path))
        with open(file_path, "w") as f:
            f.write(contents)
            self.statusBar.showMessage("Exported in plain text format")

    def export_tape(self):
        selected_folder = pathlib.Path(self.file_name) / "export"
        selected_file = QFileDialog.getSaveFileName(
            self,
            _("Export Transcript"),
            str(selected_folder.joinpath(self.file_name.stem).with_suffix(".tape"))
            , _("Tape (*.tape)")
        )
        if not selected_file[0]:
            return
        tape_contents = self.strokeList.document().toPlainText()
        tape_lines = tape_contents.splitlines()
        doc_lines = []
        for line in tape_lines:
            doc_lines.append(line.split("|")[3])
        with open(selected_file[0], "w", encoding = "utf-8") as f:
            for line in doc_lines:
                f.write(f"{line}\n")

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
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return        
        self.save_file()
        log.debug(f"Exporting in ASCII to {selected_file[0]}")
        self.thread = QThread()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(self.backup_document))
        self.progressBar.setFormat("Export transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        self.worker = documentWorker(deepcopy(self.backup_document), selected_file[0], deepcopy(self.config), deepcopy(self.styles), deepcopy(self.user_field_dict), self.file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.save_ascii)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.statusBar.showMessage("Exported in ASCII format."))
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start() 

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
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return        
        self.save_file()
        log.debug(f"Exporting in HTML to {selected_file[0]}")
        self.thread = QThread()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(self.backup_document))
        self.progressBar.setFormat("Export transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        self.worker = documentWorker(deepcopy(self.backup_document), selected_file[0], deepcopy(self.config), deepcopy(self.styles), deepcopy(self.user_field_dict), self.file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.save_html)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.statusBar.showMessage("Exported in HTML format."))
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()          

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
        log.debug(f"Exporting in plain ASCII to {selected_file[0]}")
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return        
        self.save_file()        
        self.thread = QThread()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(self.backup_document))
        self.progressBar.setFormat("Export transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        self.worker = documentWorker(deepcopy(self.backup_document), selected_file[0], deepcopy(self.config), deepcopy(self.styles), deepcopy(self.user_field_dict), self.file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.save_plain_ascii)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.statusBar.showMessage("Exported in plain ASCII format."))
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()        

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
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return        
        self.save_file()
        self.thread = QThread()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(self.backup_document))
        self.progressBar.setFormat("Export transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        self.worker = documentWorker(deepcopy(self.backup_document), selected_file[0], deepcopy(self.config), deepcopy(self.styles), deepcopy(self.user_field_dict), self.file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.save_srt)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.statusBar.showMessage("Exported in srt format."))
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        
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
        log.debug(f"Exporting in ODF to {selected_file[0]}")
        # automatically update config and save in case changes were not saved before
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return        
        self.save_file()
        self.thread = QThread()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(self.backup_document))
        self.progressBar.setFormat("Export transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        self.worker = documentWorker(deepcopy(self.backup_document), selected_file[0], deepcopy(self.config), deepcopy(self.styles), deepcopy(self.user_field_dict), self.file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.save_odf)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.statusBar.showMessage("Exported in Open Document Format."))
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
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
        log.debug(f"Import RTF {selected_file[0]}.")            
        if not self.textEdit.document().isEmpty():
            user_choice = QMessageBox.question(self, "Import RTF", "Are you sure you want to import? This erases the present transcript.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if user_choice == QMessageBox.Yes:
                log.debug("User choice to import and erase present document.")
                pass
            else:
                log.debug("Abort import.")
                return
        self.textEdit.clear()
        self.statusBar.showMessage("Parsing RTF.")
        self.progressBar = QProgressBar(self)
        self.statusBar.addWidget(self.progressBar)
        # self.progressBar.show()
        parse_results = rtf_steno(selected_file[0], self.progressBar)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        parse_results.parse_document()
        QApplication.restoreOverrideCursor()
        style_dict, renamed_indiv_style = load_rtf_styles(parse_results)
        rtf_paragraphs = parse_results.paragraphs
        for ind, par in rtf_paragraphs.items():
            par["style"] = renamed_indiv_style[int(ind)]
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
        log.debug("RTF Loading finished.")                

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
        log.debug(f"Exporting in RTF to {selected_file[0]}")            
        # automatically update config and save in case changes were not saved before
        if self.thread and self.thread.isRunning():
            QMessageBox.warning(self, "Export", "Another export is in process.")
            return        
        self.save_file()
        self.thread = QThread()
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(len(self.backup_document))
        self.progressBar.setFormat("Export transcript paragraph %v")
        self.statusBar.addWidget(self.progressBar)
        self.progressBar.show()
        self.worker = documentWorker(deepcopy(self.backup_document), selected_file[0], deepcopy(self.config), deepcopy(self.styles), deepcopy(self.user_field_dict), self.file_name)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.save_rtf)
        self.worker.progress.connect(self.progressBar.setValue)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(lambda: self.statusBar.showMessage("Exported in RTF/CRE format."))
        # self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

