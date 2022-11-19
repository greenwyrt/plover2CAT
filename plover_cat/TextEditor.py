import string

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QCursor, QKeySequence, QTextCursor
from PyQt5.QtCore import QFile, QStringListModel, Qt, QModelIndex, pyqtSignal
from PyQt5.QtWidgets import QPlainTextEdit, QCompleter

from plover_cat.main_window import BlockUserData, steno_insert, stroke_pos_at_pos

class PloverCATEditor(QPlainTextEdit):
    complete = pyqtSignal(QModelIndex)
    def __init__(self, widget):
        super().__init__(widget)
    #    self.test = "This is a string"
        self._completer = None
    def setCompleter(self, c):
        if self._completer is not None:
            self._completer.activated.disconnect()
        if not c:
            return
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
        # steno = completion.data(QtCore.Qt.UserRole)
        # text = completion.data()
        # current_cursor = self.textCursor()
        # print(self.parent().undo_stack.count())
        # print(completion_item.data())
        # tc = self.textCursor()
        # extra = len(completion) - len(self._completer.completionPrefix())
        # tc.movePosition(QTextCursor.Left)
        # tc.movePosition(QTextCursor.EndOfWord)
        # tc.insertText(completion[-extra:])
        # self.setTextCursor(tc)
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