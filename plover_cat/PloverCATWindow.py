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
from plover_cat.TextEditor import PloverCATEditor
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
        # self.player = QMediaPlayer()
        # self.recorder = QAudioRecorder()
        # # self.player.videoAvailableChanged.connect(self.set_up_video)
        # self.audio_device.addItems(self.recorder.audioInputs())
        # self.audio_codec.addItems(self.recorder.supportedAudioCodecs())
        # self.audio_container.addItems(self.recorder.supportedContainers())
        # self.audio_sample_rate.addItems([str(rate) for rate in reversed(self.recorder.supportedAudioSampleRates()[0]) if rate < 50000])
        # self.audio_channels.addItem("Default", -1)
        # self.audio_channels.addItem("1-channel", 1)
        # self.audio_channels.addItem("2-channel", 2)
        # self.audio_channels.addItem("4-channel", 4)
        # self.audio_bitrate.addItem("Default", -1)
        # self.audio_bitrate.addItem("32000", 32000)
        # self.audio_bitrate.addItem("64000", 64000)
        # self.audio_bitrate.addItem("96000", 96000)
        # self.audio_bitrate.addItem("128000", 128000)
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
            self.suggest_source.setCurrentIndex(settings.value("suggestionsource"))
        if settings.contains("recentfiles"):
            self.recent_file_menu()
        self.textEdit = None
        self.index_dialog = indexDialogWindow({})
        self.caption_dialog = captionDialogWindow() 
        self.suggest_dialog = suggestDialogWindow(None, self.engine, scowl)
        self.cap_worker = None
        self.autosave_time = QTimer()
        # self.actionUndo = self.undo_stack.createUndoAction(self)
        # undo_icon = QtGui.QIcon()
        # undo_icon.addFile(":/arrow-curve-180.png", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        # self.actionUndo.setIcon(undo_icon)
        # self.actionUndo.setShortcutContext(QtCore.Qt.WindowShortcut)
        # self.actionUndo.setToolTip("Undo writing or other action")
        # self.actionUndo.setShortcut("Ctrl+Z")
        # self.actionUndo.setObjectName("actionUndo")
        # self.actionRedo = self.undo_stack.createRedoAction(self)
        # redo_icon = QtGui.QIcon()
        # redo_icon.addFile(":/arrow-curve.png", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        # self.actionRedo.setIcon(redo_icon)
        # self.actionRedo.setShortcutContext(QtCore.Qt.WindowShortcut)
        # self.actionRedo.setToolTip("Redo writing or other action")
        # self.actionRedo.setShortcut("Ctrl+Y")
        # self.actionRedo.setObjectName("actionRedo")
        # self.menuEdit.addSeparator()
        # self.menuEdit.addAction(self.actionUndo)
        # self.menuEdit.addAction(self.actionRedo)
        # self.undoView.setStack(self.undo_stack)
        self.cutcopy_storage = deque(maxlen = 5)
        self.thread = QThread()
        self.progressBar = QProgressBar()
        self.caption_cursor_pos = 0
        self.actionUndo = None
        self.actionRedo = None
        self.menu_enabling()
        self.set_shortcuts()
        # self.update_field_menu()
        # self.update_style_menu()
        # connections:
        ## engine connections
        engine.signal_connect("stroked", self.on_stroke) 
        engine.signal_connect("stroked", self.log_to_tape) 
        engine.signal_connect("send_string", self.on_send_string)
        engine.signal_connect("send_backspaces", self.count_backspaces)     
        ## file setting/saving
        self.actionQuit.triggered.connect(lambda: self.action_close())
        self.actionOpen.triggered.connect(lambda: self.open_file())
        self.actionNew.triggered.connect(lambda: self.create_new())
        # self.actionClose.triggered.connect(lambda: self.close_file())
        # self.actionSave.triggered.connect(lambda: self.save_file())
        # self.actionSaveAs.triggered.connect(lambda: self.save_as_file())
        # self.menuRecentFiles.triggered.connect(self.recentfile_open)
        # self.actionEnableAutosave.triggered.connect(self.autosave_setup)
        # self.actionSetAutosaveTime.triggered.connect(self.set_autosave_time)
        # self.autosave_time.timeout.connect(self.autosave)
        # self.actionOpenTranscriptFolder.triggered.connect(lambda: self.open_root())
        # self.actionImportRTF.triggered.connect(lambda: self.import_rtf())
        # ## audio connections
        # self.actionOpenAudio.triggered.connect(lambda: self.open_audio())
        # self.actionPlayPause.triggered.connect(self.play_pause)
        # self.actionStopAudio.triggered.connect(self.stop_play)
        # self.playRate.valueChanged.connect(self.update_playback_rate)
        # self.player.durationChanged.connect(self.update_duration)
        # self.player.positionChanged.connect(self.update_seeker_track)
        # self.audio_seeker.sliderMoved.connect(self.set_position)
        # self.actionSkipForward.triggered.connect(lambda: self.seek_position())
        # self.actionSkipBack.triggered.connect(lambda: self.seek_position(-1))
        # self.actionRecordPause.triggered.connect(lambda: self.record_or_pause())
        # self.actionStopRecording.triggered.connect(lambda: self.stop_record())
        # self.recorder.error.connect(lambda: self.recorder_error())
        # self.recorder.durationChanged.connect(self.update_record_time)
        # self.actionShowVideo.triggered.connect(lambda: self.show_hide_video())
        # self.actionCaptioning.triggered.connect(self.setup_captions)
        # self.actionFlushCaption.triggered.connect(self.flush_caption)
        # self.actionAddChangeAudioTimestamps.triggered.connect(self.modify_audiotime)
        # ## editor related connections
        # self.actionClearParagraph.triggered.connect(lambda: self.reset_paragraph())
        # self.textEdit.complete.connect(self.insert_autocomplete)
        # self.textEdit.cursorPositionChanged.connect(self.update_gui)
        # self.editorCheck.stateChanged.connect(self.editor_lock)
        # self.submitEdited.clicked.connect(self.edit_user_data)
        self.actionCopy.triggered.connect(lambda: self.cut_steno(cut = False))
        self.actionCut.triggered.connect(lambda: self.cut_steno())
        self.actionPaste.triggered.connect(lambda: self.paste_steno())
        self.menuClipboard.triggered.connect(self.paste_steno)
        # self.undo_stack.indexChanged.connect(self.check_undo_stack)
        self.actionJumpToParagraph.triggered.connect(self.jump_par)
        self.navigationList.itemDoubleClicked.connect(self.heading_navigation)
        # self.revert_version.clicked.connect(self.revert_file)
        # ## insert related
        # self.textEdit.send_del.connect(self.mock_del)
        # self.textEdit.send_key.connect(self.mock_key)
        # self.textEdit.send_bks.connect(self.mock_bks)
        # self.actionInsertImage.triggered.connect(lambda: self.insert_image())
        # self.actionInsertNormalText.triggered.connect(self.insert_text)
        # self.actionEditFields.triggered.connect(self.edit_fields)
        # self.menuField.triggered.connect(self.insert_field)
        # self.reveal_steno_refresh.clicked.connect(self.refresh_steno_display)
        # self.actionAutomaticAffixes.toggled.connect(self.enable_affix)
        # self.actionEditAffixes.triggered.connect(self.edit_auto_affixes)
        # self.menuIndexEntry.triggered.connect(lambda action, el = None: self.insert_index_entry(el = el, action = action))
        # self.actionEditIndices.triggered.connect(self.edit_indices)
        # self.actionRedact.triggered.connect(self.insert_redacted)     
        # ## steno related edits
        # self.actionMergeParagraphs.triggered.connect(lambda: self.merge_paragraphs())
        # self.actionSplitParagraph.triggered.connect(lambda: self.split_paragraph())
        # self.actionRetroactiveDefine.triggered.connect(lambda: self.define_retroactive())
        # self.actionDefineLast.triggered.connect(lambda: self.define_scan())
        # self.actionDeleteLast.triggered.connect(lambda: self.delete_scan())
        # self.actionAutocompletion.triggered.connect(self.setup_completion)
        # self.actionAddAutocompletionTerm.triggered.connect(self.add_autocomplete_item)
        # self.actionTranslateTape.triggered.connect(self.tape_translate)
        # ## dict related
        # self.actionAddCustomDict.triggered.connect(lambda: self.add_dict())
        # self.actionRemoveTranscriptDict.triggered.connect(lambda: self.remove_dict())
        # self.actionTranscriptSuggestions.triggered.connect(lambda: self.transcript_suggest())
        # ## style connections
        # self.edit_page_layout.clicked.connect(self.update_config)
        # self.editCurrentStyle.clicked.connect(self.style_edit)
        # self.actionCreateNewStyle.triggered.connect(self.new_style)
        # self.actionRefreshEditor.triggered.connect(self.refresh_editor_styles)
        # self.actionStyleFileSelect.triggered.connect(self.select_style_file)
        # self.actionGenerateStyleFromTemplate.triggered.connect(self.style_from_template)
        # self.style_selector.activated.connect(self.update_paragraph_style)
        # self.blockFont.currentFontChanged.connect(self.calculate_space_width)
        # self.menuParagraphStyle.triggered.connect(self.change_style)
        # # self.textEdit.ins.connect(self.change_style)
        # ## view
        self.actionWindowFont.triggered.connect(lambda: self.change_window_font())
        self.actionBackgroundColor.triggered.connect(lambda: self.change_backgrounds())
        # self.actionShowAllCharacters.triggered.connect(lambda: self.show_invisible_char())
        self.actionPaperTapeFont.triggered.connect(lambda: self.change_tape_font())
        ## tools
        self.actionStyling.triggered.connect(lambda: self.show_toolbox_pane(self.styling_pane))
        self.actionPageFormat.triggered.connect(lambda: self.show_toolbox_pane(self.page_format_pane))
        # self.actionFindReplacePane.triggered.connect(lambda: self.show_find_replace())
        self.actionParagraph.triggered.connect(lambda: self.show_toolbox_pane(self.paragraph_pane))
        self.actionAudioRecording.triggered.connect(lambda: self.show_toolbox_pane(self.audio_recording_pane))
        self.actionSpellcheck.triggered.connect(lambda: self.show_toolbox_pane(self.spellcheck_pane))
        # self.actionStenoSearch.triggered.connect(lambda: self.show_stenospell())
        self.actionSearchWikipedia.triggered.connect(lambda: self.search_online("https://en.wikipedia.org/wiki/Special:Search/{0}"))
        self.actionSearchMerriamWebster.triggered.connect(lambda: self.search_online("http://www.merriam-webster.com/dictionary/{0}"))
        self.actionSearchOED.triggered.connect(lambda: self.search_online("https://www.oed.com/search/dictionary/?scope=Entries&q={0}"))
        self.actionSearchGoogle.triggered.connect(lambda: self.search_online("https://www.google.com/search?q={0}"))
        self.actionSearchDuckDuckGo.triggered.connect(lambda: self.search_online("https://duckduckgo.com/?q={0}"))
        # ## search/replace connections
        # self.search_text.toggled.connect(lambda: self.search_text_options())
        # self.search_steno.toggled.connect(lambda: self.search_steno_options())
        # self.search_untrans.toggled.connect(lambda: self.search_untrans_options())
        # self.search_forward.clicked.connect(lambda: self.search())
        # self.search_backward.clicked.connect(lambda: self.search(-1))
        # self.replace_selected.clicked.connect(lambda: self.replace())
        # self.replace_all.clicked.connect(lambda: self.replace_everything())
        # ## spellcheck
        # self.dictionary = Dictionary.from_files('en_US')
        # self.spell_search.clicked.connect(lambda: self.spellcheck())
        # self.spell_skip.clicked.connect(lambda: self.spellcheck())
        # self.spell_ignore_all.clicked.connect(lambda: self.sp_ignore_all())
        # self.spellcheck_suggestions.itemDoubleClicked.connect(self.sp_insert_suggest)
        # self.dict_selection.activated.connect(self.set_sp_dict)
        # ## steno search
        # self.steno_search.clicked.connect(lambda: self.spell_steno())
        # ## suggestions
        # self.suggest_sort.toggled.connect(lambda: self.get_suggestions())
        # self.suggest_source.currentIndexChanged.connect(lambda: self.get_suggestions())
        # ## tape
        # self.textEdit.document().blockCountChanged.connect(lambda: self.get_suggestions())
        # self.numbers = {number: letter for letter, number in plover.system.NUMBERS.items()}
        # self.strokeLocate.clicked.connect(lambda: self.stroke_to_text_move())
        # # export
        # self.actionPlainText.triggered.connect(lambda: self.export_text())
        # self.actionASCII.triggered.connect(lambda: self.export_ascii())
        # self.actionPlainASCII.triggered.connect(lambda: self.export_plain_ascii())
        # self.actionHTML.triggered.connect(lambda: self.export_html())
        # self.actionSubRip.triggered.connect(lambda: self.export_srt())
        # self.actionODT.triggered.connect(lambda: self.export_odt())
        # self.actionRTF.triggered.connect(lambda: self.export_rtf())
        # self.actionTape.triggered.connect(lambda: self.export_tape())
        # help
        self.actionUserManual.triggered.connect(lambda: self.open_help())
        self.actionAbout.triggered.connect(lambda: self.about())
        self.actionAcknowledgements.triggered.connect(lambda: self.acknowledge())
        self.actionEditMenuShortcuts.triggered.connect(self.edit_shortcuts)
        # status bar
        self.cursor_status = QLabel("Par,Char: {line},{char}".format(line = 0, char = 0))
        self.cursor_status.setObjectName("cursor_status")
        self.statusBar.addPermanentWidget(self.cursor_status)
        self.display_message("Create New Transcript or Open Existing...")
        log.debug("Main window open.")
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

    def display_message(self, txt):
        self.statusBar.showMessage(txt)
        log.debug(txt)

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
        self.menuInsert.setEnabled(not value)
        self.menuAudio.setEnabled(not value)
        self.menuStyling.setEnabled(not value)
        self.menuDictionary.setEnabled(not value)
        self.menuTools.setEnabled(not value)
        self.menuExport_as.setEnabled(not value)
        self.toolbarSteno.setEnabled(not value)
        self.toolbarAudio.setEnabled(not value)
        self.toolbarEdit.setEnabled(not value)
        self.actionNew.setEnabled(value)
        self.actionOpen.setEnabled(value)
        self.actionImportRTF.setEnabled(not value)
        self.actionSave.setEnabled(not value)
        self.actionSaveAs.setEnabled(not value)
        self.actionOpenTranscriptFolder.setEnabled(not value)
        self.actionClose.setEnabled(not value)

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

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

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

    def search_online(self, link):
        current_cursor = self.textEdit.textCursor()
        if not current_cursor.hasSelection():
            self.display_message("No text selected for online search.")
            return
        QDesktopServices.openUrl(QUrl(link.format(current_cursor.selectedText())))

    def heading_navigation(self, item):
        block_number = item.data(Qt.UserRole)
        log.debug(f"User navigating to block {block_number}.")
        self.textEdit.navigate_to(block_number)

    def jump_par(self):
        current_cursor = self.textEdit.textCursor()
        max_blocks = self.textEdit.document().blockCount()
        current_block_num = current_cursor.blockNumber()
        block_num, ok = QInputDialog().getInt(self, "Jump to paragraph...", "Paragraph (0-based): ", current_block_num, 0, max_blocks)
        if ok:
            log.debug(f"User set jump to block {block_num}")
            self.textEdit.navigate_to(block_num)

    def clipboard_menu(self):
        self.menuClipboard.clear()
        for ind, snippet in enumerate(self.cutcopy_storage):
            label = snippet.to_text()
            action = QAction(label, self.menuClipboard)
            action.setObjectName(f"clipboard{ind}")
            action.setData(ind)
            self.menuClipboard.addAction(action)

    def create_new(self):
        transcript_name = "transcript-" + datetime.now().strftime("%Y-%m-%dT%H%M%S")
        transcript_dir = pathlib.Path(plover.oslayer.config.CONFIG_DIR)
        default_path = transcript_dir / transcript_name
        # newer creation wizard should be here to add additional dictionaries, spellcheck and other data
        selected_name = QFileDialog.getSaveFileName(self, _("Transcript name and location"), str(default_path))[0]
        if not selected_name:
            return
        self.display_message(f"Creating project files at {str(selected_name)}")
        self.open_file(selected_name)

    def open_file(self, file_path = None):
        if not file_path:
            name = "Config"
            extension = "config"
            selected_folder = QFileDialog.getOpenFileName( self, _("Open " + name), plover.oslayer.config.CONFIG_DIR, _(name + "(*." + extension + ")"))[0]
            if not selected_folder:
                self.display_message("No config file was selected for loading.")
                return
            selected_folder = pathlib.Path(selected_folder).parent
        else:
            selected_folder = pathlib.Path(file_path)
        self.display_message(f"Loading project files from {str(selected_folder)}")   
        editorTab = QtWidgets.QWidget()
        editorTab.setObjectName(f"editorTab{self.mainTabs.count()}")
        editorLayout = QtWidgets.QHBoxLayout(editorTab)
        editorLayout.setObjectName(f"editorLayout{self.mainTabs.count()}")
        self.textEdit = PloverCATEditor(editorTab)
        self.textEdit.load(selected_folder, self.engine)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textEdit.sizePolicy().hasHeightForWidth())
        self.textEdit.setSizePolicy(sizePolicy) 
        editorLayout.addWidget(self.textEdit)
        tab_index = self.mainTabs.addTab(editorTab, self.textEdit.file_name.name)  
        self.mainTabs.setCurrentIndex(tab_index)
        self.setup_connections()

    def setup_connections(self):
        if self.actionUndo:
            self.menuEdit.removeAction(self.actionUndo)
        if self.actionRedo:
            self.menuEdit.removeAction(self.actionRedo)
        self.actionUndo = self.textEdit.undo_stack.createUndoAction(self.menuEdit)
        undo_icon = QtGui.QIcon()
        undo_icon.addFile(":/arrow-curve-180.png", QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.actionUndo.setIcon(undo_icon)
        self.actionUndo.setShortcutContext(QtCore.Qt.WindowShortcut)
        self.actionUndo.setToolTip("Undo writing or other action")
        self.actionUndo.setShortcut("Ctrl+Z")
        self.actionUndo.setObjectName("actionUndo")
        self.actionRedo = self.textEdit.undo_stack.createRedoAction(self.menuEdit)
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
        self.menu_enabling(False)
        # needed to override default undo/redo shortcuts
        self.set_shortcuts()
        self.textEdit.customContextMenuRequested.connect(self.context_menu)
        self.textEdit.send_message.connect(self.display_message)  

    def action_close(self):
        log.debug("User selected quit.")
        settings = QSettings("Plover2CAT", "OpenCAT")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowstate", self.saveState())
        settings.setValue("windowfont", self.font().toString())
        settings.setValue("tapefont", self.strokeList.font().toString())
        settings.setValue("backgroundcolor", self.palette().color(QPalette.Base))
        settings.setValue("suggestionsource", int(self.suggest_source.currentIndex()))
        log.info("Saved window settings")
        choice = self.textEdit.close_transcript()
        if choice:
            log.debug("Closing window.")
            self.parent().close()

    def save_file(self):
        pass
    def save_as_file(self):
        pass
    def autosave(self):
        pass
    def log_to_tape(self, stroke):
        pass   
    def on_send_string(self, string):
        log.debug(f"Plover engine sent string: {string}")
        self.textEdit.last_string_sent = string
    def count_backspaces(self, backspace):
        log.debug(f"Plover engine sent {backspace} backspace(s)")
        self.textEdit.last_backspaces_sent = backspace
    def on_stroke(self, stroke_pressed):
        self.editorCheck.setChecked(True)
        if not self.textEdit:
            return
        if not self.engine.output:
            return
        # do nothing if window not in focus
        if not self.textEdit.isActiveWindow() and not self.actionCaptureAllOutput.isChecked():
            return
        # case if stroke only sends commands
        if not self.textEdit.last_string_sent and self.textEdit.last_backspaces_sent == 0:
            return
        # self.display_captions()
        self.textEdit.on_stroke(stroke_pressed, self.actionCursorAtEnd.isChecked())

    def cut_steno(self, cut = True):
        res = self.textEdit.cut_steno(cut = cut)
        self.cutcopy_storage.appendleft(res)
        self.clipboard_menu()

    def paste_steno(self, action = None):
        log.debug("Performing pasting.")
        index = 0
        if action:
            index = action.data()
        store_data = deepcopy(self.cutcopy_storage[index])
        if store_data == "":
            self.display_message("Nothing in clipboard. Cut or copy text to paste.")
            return
        ea = element_actions()
        current_cursor = self.textEdit.textCursor()
        current_block_num = current_cursor.blockNumber()
        current_block = self.textEdit.document().findBlockByNumber(current_block_num)
        start_pos = min(current_cursor.position(), current_cursor.anchor()) - current_block.position()
        self.textEdit.undo_stack.beginMacro(f"Paste: {store_data.to_text()}")
        self.textEdit.blockSignals(True)
        for el in store_data.data:
            current_block = self.textEdit.textCursor().blockNumber()
            current_pos = self.textEdit.textCursor().positionInBlock()
            cmd = ea.make_action(self.textEdit, current_block, current_pos, el)
            self.textEdit.undo_stack.push(cmd)
        self.textEdit.blockSignals(False)
        self.undo_stack.endMacro()
        self.display_message(f"Pasting to paragraph {current_block_num} at position {start_pos}.")  
