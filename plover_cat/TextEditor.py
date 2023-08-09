import string

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QCursor, QKeySequence, QTextCursor
from PyQt5.QtCore import QFile, QStringListModel, Qt, QModelIndex, pyqtSignal
from PyQt5.QtWidgets import QPlainTextEdit, QCompleter, QTextEdit

from plover_cat.main_window import BlockUserData, steno_insert

num_keys = [Qt.Key_0, Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9]

class PloverCATEditor(QTextEdit):
    complete = pyqtSignal(QModelIndex)
    send_key = pyqtSignal(str)
    send_del = pyqtSignal()
    send_bks = pyqtSignal()
    def __init__(self, widget):
        super().__init__(widget)
        self._completer = None
        self.block = 0
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