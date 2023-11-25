import os
import subprocess
import string
import re
import pathlib
import json
import textwrap
from datetime import datetime, timezone
import time
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
        self.video = None
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
        self.cutcopy_storage = deque(maxlen = 5)
        self.thread = QThread()
        self.progressBar = QProgressBar()
        self.caption_cursor_pos = 0
        self.actionUndo = None
        self.actionRedo = None
        self.menu_enabling()
        self.audio_menu_enabling(False)
        self.set_shortcuts()
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
        self.actionClose.triggered.connect(lambda: self.close_file())
        self.actionSave.triggered.connect(lambda: self.save_file())
        # self.actionSaveAs.triggered.connect(lambda: self.save_as_file())
        # self.menuRecentFiles.triggered.connect(self.recentfile_open)
        self.actionEnableAutosave.triggered.connect(self.autosave_setup)
        self.actionSetAutosaveTime.triggered.connect(self.set_autosave_time)
        self.autosave_time.timeout.connect(self.autosave)
        self.actionOpenTranscriptFolder.triggered.connect(lambda: self.open_root())
        # self.actionImportRTF.triggered.connect(lambda: self.import_rtf())
        ## audio connections
        self.actionOpenAudio.triggered.connect(lambda: self.open_audio())
        # self.actionRecordPause.triggered.connect(lambda: self.record_or_pause())
        # self.actionStopRecording.triggered.connect(lambda: self.stop_record())
        # self.recorder.error.connect(lambda: self.recorder_error())
        # self.recorder.durationChanged.connect(self.update_record_time)
        self.actionShowVideo.triggered.connect(lambda: self.show_hide_video())
        # self.actionCaptioning.triggered.connect(self.setup_captions)
        # self.actionFlushCaption.triggered.connect(self.flush_caption)
        # self.actionAddChangeAudioTimestamps.triggered.connect(self.modify_audiotime)
        ## editor related connections
        self.actionClearParagraph.triggered.connect(lambda: self.reset_paragraph())
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
        self.actionRevertTranscript.triggered.connect(self.revert_file)
        ## insert related
        self.actionInsertImage.triggered.connect(lambda: self.insert_image())
        self.actionInsertNormalText.triggered.connect(self.insert_text)
        self.actionEditFields.triggered.connect(self.edit_fields)
        self.menuField.triggered.connect(self.insert_field)
        self.reveal_steno_refresh.clicked.connect(self.refresh_steno_display)
        self.actionAutomaticAffixes.toggled.connect(self.enable_affix)
        self.actionEditAffixes.triggered.connect(self.edit_auto_affixes)
        self.menuIndexEntry.triggered.connect(lambda action, el = None: self.insert_index_entry(el = el, action = action))
        self.actionEditIndices.triggered.connect(self.edit_indices)
        # self.actionRedact.triggered.connect(self.insert_redacted)     
        ## steno related edits
        self.actionMergeParagraphs.triggered.connect(lambda: self.merge_paragraphs())
        self.actionSplitParagraph.triggered.connect(lambda: self.split_paragraph())
        # self.actionRetroactiveDefine.triggered.connect(lambda: self.define_retroactive())
        # self.actionDefineLast.triggered.connect(lambda: self.define_scan())
        # self.actionDeleteLast.triggered.connect(lambda: self.delete_scan())
        # self.actionAutocompletion.triggered.connect(self.setup_completion)
        # self.actionAddAutocompletionTerm.triggered.connect(self.add_autocomplete_item)
        # self.actionTranslateTape.triggered.connect(self.tape_translate)
        ## dict related
        self.actionAddCustomDict.triggered.connect(lambda: self.add_dict())
        self.actionRemoveTranscriptDict.triggered.connect(lambda: self.remove_dict())
        self.actionTranscriptSuggestions.triggered.connect(lambda: self.transcript_suggest())
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
        self.actionShowAllCharacters.triggered.connect(lambda: self.show_invisible_char())
        self.actionPaperTapeFont.triggered.connect(lambda: self.change_tape_font())
        ## tools
        self.actionStyling.triggered.connect(lambda: self.show_toolbox_pane(self.styling_pane))
        self.actionPageFormat.triggered.connect(lambda: self.show_toolbox_pane(self.page_format_pane))
        self.actionFindReplacePane.triggered.connect(lambda: self.show_find_replace())
        self.actionParagraph.triggered.connect(lambda: self.show_toolbox_pane(self.paragraph_pane))
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

    def update_tape(self, txt):
        # todo: if ever tape format changes, alter here
        lines = txt.splitlines()
        for line in lines:
            self.strokeList.appendPlainText(line)

    def display_block_steno(self, strokes):
        # clear of last block data
        self.parSteno.clear()
        for ind, el in enumerate(strokes.data):
            item = QListWidgetItem()
            item.setText(el.to_text())
            item.setData(Qt.ToolTipRole, el.to_display())
            item.setData(Qt.UserRole, ind)
            self.parSteno.addItem(item)     

    def refresh_steno_display(self):
        current_cursor = self.textEdit.textCursor()
        block_strokes = current_cursor.block().userData()["strokes"]
        self.display_block_steno(block_strokes)

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

    def audio_menu_enabling(self, value = True):
        self.actionOpenAudio.setEnabled(not value)
        self.actionPlayPause.setEnabled(value)
        self.actionStopAudio.setEnabled(value)
        self.actionSkipForward.setEnabled(value)
        self.actionSkipBack.setEnabled(value)
        self.actionSpeedUp.setEnabled(value)
        self.actionSlowDown.setEnabled(value)
        self.playRate.setEnabled(value)
        self.audioDelay.setEnabled(value)
        self.audio_seeker.setEnabled(value)
        if not self.textEdit:
            return
        if value:
            label_text = "Audio:" + str(self.textEdit.audio_file.name)
            self.audio_label.setText(label_text)
            self.actionPlayPause.triggered.connect(self.textEdit.play_pause_audio)
            self.actionStopAudio.triggered.connect(self.textEdit.player.stop)
            self.update_seeker_track(self.textEdit.audio_position)
            self.update_duration(self.textEdit.player.duration())
            self.audio_seeker.sliderMoved.connect(self.textEdit.player.setPosition)
            self.textEdit.audio_position_changed.connect(self.update_seeker_track)
            self.textEdit.audio_length_changed.connect(self.update_duration)
            self.actionSkipForward.triggered.connect(lambda: self.textEdit.player.setPosition(self.textEdit.player.position() + 5000))
            self.actionSkipBack.triggered.connect(lambda: self.textEdit.player.setPosition(self.textEdit.player.position() - 5000))
            self.playRate.valueChanged.connect(self.textEdit.player.setPlaybackRate)
            self.audioDelay.setValue(self.textEdit.audio_delay)
            self.audioDelay.valueChanged.connect(self.set_audio_delay)
        else:
            self.audio_label.setText("Select file to play audio")
            self.actionPlayPause.triggered.disconnect()
            self.actionStopAudio.triggered.disconnect()
            self.audio_seeker.sliderMoved.disconnect()
            self.actionSkipForward.triggered.disconnect()
            self.actionSkipBack.triggered.disconnect()
            self.playRate.valueChanged.disconnect()
            self.playRate.setValue(1)
            self.update_duration(0)
            self.update_seeker_track(0)
            self.audioDelay.valueChanged.disconnect()
            self.audioDelay.setValue(0)

    def update_duration(self, duration):
        self.audio_seeker.setMaximum(duration)
        self.audio_duration.setText(ms_to_hours(duration))

    def update_seeker_track(self, position):
        self.audio_seeker.setValue(position)
        self.audio_curr_pos.setText(ms_to_hours(position))

    def open_root(self):
        selected_folder = pathlib.Path(self.textEdit.file_name)
        self.display_message(f"User open file directory {str(selected_folder)}")
        if platform.startswith("win"):
            os.startfile(selected_folder)
        elif platform.startswith("linux"):
            subprocess.call(['xdg-open', selected_folder])
        elif platform.startswith("darwin"):
            subprocess.call(['open', selected_folder])
        else:
            self.display_message("Unknown operating system. Not opening file directory.")

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

    def show_invisible_char(self):
        doc_options = self.textEdit.document().defaultTextOption()
        if self.actionShowAllCharacters.isChecked():
            self.display_message("User enabled show invisible characters.")      
            doc_options.setFlags(doc_options.flags() | QTextOption.ShowTabsAndSpaces | QTextOption.ShowLineAndParagraphSeparators)
        else:
            self.display_message("User disabled show invisible characters.")      
            doc_options.setFlags(doc_options.flags() & ~QTextOption.ShowTabsAndSpaces & ~QTextOption.ShowLineAndParagraphSeparators)
        self.textEdit.document().setDefaultTextOption(doc_options)

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

    def update_config_gui(self):
        self.update_field_menu()
        # todo: update page dimensions here

    def update_field_menu(self):
        self.display_message("Updating field sub-menu.")
        self.menuField.clear()
        for ind, (k, v) in enumerate(self.textEdit.user_field_dict.items()):
            label = "{%s}: %s" % (k, v)
            action = QAction(label, self.menuField)
            if ind < 10:           
                action.setShortcut("Ctrl+Shift+%d" % ind)
            action.setData(k)
            self.menuField.addAction(action)

    def update_index_menu(self, index_dict = None):
        if not index_dict:
            index_dict = self.textEdit.extract_indexes()
        self.display_message("Updating index entry insertion sub-menu.")
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
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.display_message(f"Loading project files from {str(selected_folder)}")   
        editorTab = QtWidgets.QWidget()
        editorTab.setObjectName(f"editorTab_{time.time()}")
        editorLayout = QtWidgets.QHBoxLayout(editorTab)
        editorLayout.setObjectName(f"editorLayout_{time.time()}")
        self.textEdit = PloverCATEditor(editorTab)
        self.textEdit.load(selected_folder, self.engine)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(3)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textEdit.sizePolicy().hasHeightForWidth())
        self.textEdit.setSizePolicy(sizePolicy) 
        editorLayout.addWidget(self.textEdit)
        tab_index = self.mainTabs.addTab(editorTab, self.textEdit.file_name.name)
        self.update_tape(self.textEdit.tape)
        self.mainTabs.setCurrentIndex(tab_index)
        QApplication.restoreOverrideCursor()
        self.setup_connections()

    def setup_connections(self):
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
        if self.textEdit.document().defaultTextOption().flags() and QTextOption.ShowTabsAndSpaces:
            self.actionShowAllCharacters.setChecked(True)
        self.menuEdit.addSeparator()
        self.menuEdit.addAction(self.actionUndo)
        self.menuEdit.addAction(self.actionRedo)
        self.menu_enabling(False)
        # needed to override default undo/redo shortcuts
        self.set_shortcuts()
        self.undoView.setStack(self.textEdit.undo_stack)
        self.update_field_menu()
        self.update_index_menu()
        self.textEdit.customContextMenuRequested.connect(self.context_menu)
        self.textEdit.send_message.connect(self.display_message)
        self.textEdit.send_tape.connect(self.update_tape) 
        self.textEdit.config_updated.connect(self.update_config_gui)
        self.textEdit.player.videoAvailableChanged.connect(self.set_up_video)
        if self.textEdit.player.isAudioAvailable():
            self.audio_menu_enabling()
            # todo read audio position and set up gui
        if self.textEdit.player.isVideoAvailable():
            self.set_up_video()

    def breakdown_connections(self):
        if self.actionUndo:
            self.menuEdit.removeAction(self.actionUndo)
            self.actionUndo.deleteLater()
        if self.actionRedo:
            self.menuEdit.removeAction(self.actionRedo)
            self.actionRedo.deleteLater()
        self.actionShowAllCharacters.setChecked(False)
        self.menu_enabling()
        self.strokeList.clear()
        self.undoView.setStack(None)
        self.menuField.clear() # clear field submenu
        self.menuIndexEntry.clear() # clear index submenu
        if self.textEdit.player.isAudioAvailable(): # clear audio connections if transcript has them
            self.textEdit.player.stop()
            self.audio_menu_enabling(False)
        if self.video:
            self.videoLayout.removeWidget(self.video)
            self.video.deleteLater()
        # todo: break all connections to textEdit
        
    def action_close(self):
        self.display_message("User selected quit.")
        settings = QSettings("Plover2CAT", "OpenCAT")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowstate", self.saveState())
        settings.setValue("windowfont", self.font().toString())
        settings.setValue("tapefont", self.strokeList.font().toString())
        settings.setValue("backgroundcolor", self.palette().color(QPalette.Base))
        settings.setValue("suggestionsource", int(self.suggest_source.currentIndex()))
        self.display_message("Saved window settings")
        choice = self.close_file()
        if choice:
            self.display_message("Closing window.")
            self.parent().close()

    def close_file(self, tab_index = None):
        if not tab_index:
            tab_index = self.mainTabs.currentIndex()
        if tab_index == -1:
            # if no tabs in widget, no closing
            return True
        tab_page = self.mainTabs.widget(tab_index)
        if tab_page.objectName().startswith("editorTab"):
            choice = self.textEdit.close_transcript()
            if choice:
                self.textEdit.disconnect()
                self.breakdown_connections()
        self.mainTabs.removeTab(tab_index)
        tab_page.deleteLater()
        return True

    def save_file(self):
        self.textEdit.save()
        self.update_commit_list()

    def save_as_file(self):
        self.textEdit.save_as()
        
    def autosave(self):
        if not self.textEdit:
            return
        self.textEdit.autosave()

    def revert_file(self):
        if not self.textEdit.repo:
            return
        if not self.textEdit.undo_stack.isClean():
            user_choice = QMessageBox.critical(self, "Revert transcript", "All unsaved changes will be destroyed upon reversion. Session history will be erased. Do you wish to continue?")
            if user_choice == QMessageBox.No:
                return
        commit_choices = self.textEdit.get_dulwich_commits()
        commit_times = [commit_time for commit_id, commit_time in commit_choices]
        commit_time, ok = QInputDialog.getItem(self, "Revert transcript", "Commit", commit_times, 0, False)
        if ok:
            ind = commit_times.index(commit_time)
            commit_id = commit_choices[ind][0]
            self.textEdit.revert_transcript(commit_id)

    def add_dict(self):
        ## select a dict from not file location to add to plover stack
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Dictionary"),
            str(self.textEdit.file_name), _("Dict (*.json)"))[0]
        if not selected_file:
            return
        selected_file = pathlib.Path(selected_file)
        self.display_message(f"Selected dictionary at {str(selected_file)} to add.")
        dict_dir_path = self.textEdit.file_name / "dict"
        try:
            os.mkdir(dict_dir_path)
        except FileExistsError:
            pass
        dict_dir_name = dict_dir_path / selected_file.name
        if selected_file != dict_dir_name:
            self.display_message(f"Copying dictionary at {str(selected_file)} to {str(dict_dir_name)}")
            copyfile(selected_file, dict_dir_name)
        transcript_dicts = self.textEdit.get_config_value("dictionaries")
        engine_dicts = self.engine.config["dictionaries"]
        # do not add if already in dict
        if str(selected_file) in engine_dicts:
            self.display_message("Selected dictionary is already in loaded dictionaries, passing.")
            return
        new_dict_config = add_custom_dicts([str(selected_file)], engine_dicts)
        self.engine.config = {'dictionaries': new_dict_config}
        # update config
        transcript_dicts.append(str(dict_dir_name.relative_to(self.textEdit.file_name)))
        self.display_message(f"Add {str(dict_dir_name.relative_to(self.textEdit.file_name))} to config")

    def remove_dict(self):
        dict_dir_path = self.textEdit.file_name / "dict"
        selected_file = QFileDialog.getOpenFileName(
            self,
            _("Select Dictionary to remove"),
            str(dict_dir_path), _("Dict (*.json)"))[0]
        if not selected_file:
            return
        selected_file = pathlib.Path(selected_file)
        self.display_message(f"Selected dictionary at {str(selected_file)} to remove.")
        dictionary_list = self.textEdit.get_config_value("dictionaries")
        list_dicts = self.engine.config["dictionaries"]
        list_dicts = [i.path for i in list_dicts if pathlib.Path(i.path) != selected_file]
        new_dict_config = add_custom_dicts(list_dicts, [])
        self.engine.config = {'dictionaries': new_dict_config}
        if str(selected_file.relative_to(self.textEdit.file_name)) in dictionary_list:
            dictionary_list = [i for i in dictionary_list if i != str(selected_file.relative_to(self.textEdit.file_name))]
            self.display_message(f"Remove {str(selected_file.relative_to(self.textEdit.file_name))} from config")
            self.textEdit.set_config_value("dictionaries", dictionary_list)
        else:
            self.display_message("Selected dictionary not a transcript dictionary, passing.")

    def transcript_suggest(self):
        self.display_message("Generate transcript suggestions.")
        if not self.suggest_dialog:
            self.suggest_dialog = suggestDialogWindow(None, self.engine, scowl)
        self.suggest_dialog.update_text(self.textEdit.toPlainText())
        self.suggest_dialog.show()      
        self.suggest_dialog.activateWindow() 

    def log_to_tape(self, stroke):
        # need file to output to
        if not self.textEdit:
            return
        if not self.engine.output and self.engine._machine_params.type == "Keyboard":
            return
        # if window inactive, and not capturing everything, and not enabled, don't do anything
        # print(self.textEdit.isActiveWindow())
        if not self.textEdit.isActiveWindow() and not self.actionCaptureAllOutput.isChecked():
            return
        ## copy from parts of plover paper tape and tapeytape
        self.textEdit.log_to_tape(stroke)             

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

    def reset_paragraph(self):
        user_choice = QMessageBox.critical(self, "Reset Paragraph", "This will clear all data from this paragraph. This cannot be undone. You will lose all history. Are you sure?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if user_choice != QMessageBox.Yes:
            return
        log.debug("User trigger paragraph reset.")
        self.textEdit.undo_stack.clear()
        log.debug("History cleared.")
        current_cursor = self.textEdit.textCursor()
        current_block = current_cursor.block()
        current_block.setUserData(BlockUserData())
        current_cursor.select(QTextCursor.BlockUnderCursor)
        current_cursor.removeSelectedText()

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
        self.textEdit.undo_stack.endMacro()
        self.display_message(f"Pasting to paragraph {current_block_num} at position {start_pos}.")  

    def enable_affix(self, check):
        self.display_message("Toggle automatic paragraph affixes.")
        self.textEdit.set_config_value("enable_automatic_affix", check)

    def edit_auto_affixes(self):
        if not self.auto_paragraph_affixes:
            self.display_message("No pre-existing affix dict.")
        self.affix_dialog = affixDialogWindow(self.auto_paragraph_affixes, [*self.styles])
        res = self.affix_dialog.exec_()
        if res == QDialog.Accepted:
            self.display_message("Updating paragraph affixes.")
            self.auto_paragraph_affixes = self.affix_dialog.affix_dict

    def insert_text(self, text = None):
        if not text:
            text, ok = QInputDialog().getText(self, "Insert Normal Text", "Text to insert")
            if not ok:
                return
        self.display_message(f"Inserting normal text {text}.")
        self.textEdit.insert_text(text)

    def insert_image(self):
        selected_file = QFileDialog.getOpenFileName(self, _("Select Image"), str(self.textEdit.file_name), 
                            _("Image Files(*.png *.jpg *jpeg)"))[0]
        if not selected_file:
            self.display_message("No image selected, aborting")
            return
        self.display_message(f"User selected image file: {selected_file}")
        selected_file = pathlib.Path(selected_file)
        asset_dir_path = self.textEdit.file_name / "assets"
        try:
            os.mkdir(asset_dir_path)
            self.display_message("Created asset directory.")
        except FileExistsError:
            pass
        asset_dir_name = asset_dir_path / selected_file.name
        if selected_file != asset_dir_name:
            self.display_message(f"Copying image at {str(selected_file)} to {str(asset_dir_name)}")
            copyfile(selected_file, asset_dir_name)
        im_element = image_text(path = asset_dir_name.as_posix())
        insert_cmd = image_insert(self.textEdit, self.textEdit.textCursor().blockNumber(), 
                        self.textEdit.textCursor().positionInBlock(), im_element)
        self.textEdit.undo_stack.push(insert_cmd)

    def insert_field(self, action):
        name = action.data()
        self.display_message(f"Insert field {name}.")
        self.textEdit.insert_field(name)

    def edit_fields(self):
        self.field_dialog = fieldDialogWindow(self.textEdit.user_field_dict)
        res = self.field_dialog.exec_()
        if res == QDialog.Accepted:
            self.textEdit.update_fields(self.field_dialog.user_field_dict)  

    def edit_indices(self, show_dialog = True):
        if not self.index_dialog:
            self.index_dialog = indexDialogWindow({})
        present_index = self.textEdit.extract_indexes()
        if present_index:
            self.index_dialog.update_dict(present_index)
        self.index_dialog.show()
        self.index_dialog.index_insert.connect(self.insert_index_entry)
        self.index_dialog.updated_dict.connect(self.update_indices)
        self.index_dialog.activateWindow()   

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
        self.textEdit.insert_index_entry(el)
        if not self.index_dialog:
            self.index_dialog = indexDialogWindow({})
        present_index = self.textEdit.extract_indexes()
        if present_index:
            self.index_dialog.update_dict(present_index)

    def update_indices(self):
        present_index = self.textEdit.extract_indexes()
        new_index = self.index_dialog.index_dict
        if not present_index:
            return
        self.textEdit.update_indices(present_index, new_index)
        self.update_index_menu(self.index_dialog.index_dict)

    def open_audio(self):
        if self.textEdit.recorder.state() == QMediaRecorder.StoppedState:
            pass
        else:
            QMessageBox.information(self, "Opening Media", "Recording in progress. Stop recording before loading media file.")
            return
        audio_file = QFileDialog.getOpenFileName(self, _("Select Media File"), str(self.textEdit.file_name), "Media Files (*.mp3 *.ogg *.wav *.mp4 *.mov *.wmv *.avi)")
        if audio_file[0]:
            self.textEdit.load_audio(audio_file[0])
            self.audio_menu_enabling()

    def set_audio_delay(self, value):
        self.textEdit.audio_delay = value

    def set_up_video(self, avail):
        if avail:
            self.display_message("Video available for file, displaying.")
            self.video = QVideoWidget()
            self.textEdit.player.setVideoOutput(self.video)
            self.videoLayout.addWidget(self.video)
            self.dockAudio.setVisible(True) 
            self.actionShowVideo.setEnabled(True)

    def show_hide_video(self):
        if self.video.isVisible():
            log.debug("Hide video.")
            self.video.hide()
        else:
            log.debug("Show video.")
            self.video.show()

    def record_or_pause(self):
        if self.textEdit.player.state() != QMediaPlayer.StoppedState:
            self.display_message("Playing in progress. Stop media first.")
            return
        else:
            pass
        if self.textEdit.recorder.state() != QMediaPlayer.RecordingState:
            self.textEdit.recorder.pause()
            self.display_message("Recording paused.")
        else:
            # todo: dialog controls, file location
            self.actionStopRecording.setEnabled(True)
            self.textEdit.recorder.play()
            self.display_message("Recording started.")

    def stop_record(self):
        self.textEdit.recorder.stop()
        self.actionStopRecording.setEnabled(False)
        self.display_message("Recording stopped.")

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