from copy import deepcopy
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTableWidgetItem, QDialog
from plover_cat.index_dialog_ui import Ui_indexDialog
from plover_cat.steno_objects import index_text

class indexDialogWindow(QDialog, Ui_indexDialog):
    index_insert = pyqtSignal(object)
    updated_dict = pyqtSignal()
    def __init__(self, index_dict):
        super().__init__()
        self.setupUi(self)
        self.index_dict = index_dict
        self.indexChoice.addItems([*self.index_dict])
        self.displayEntries.setColumnCount(2)
        self.displayEntries.setHorizontalHeaderLabels(["Name", "Description"])
        self.displayEntries.itemSelectionChanged.connect(self.enable_insert)
        self.indexChoice.activated.connect(self.update_display)
        self.indexChoice.currentIndexChanged.connect(self.enable_add)
        self.saveIndex.clicked.connect(self.save_index)
        self.saveAndInsert.clicked.connect(self.insert_entry)
        self.addNewIndex.clicked.connect(self.new_index)
        self.entryAdd.clicked.connect(self.add_new_entry)
    def update_display(self, index):
        self.indexChoice.setCurrentIndex(index)
        self.indexPrefix.clear()
        if not self.hideDescript.isChecked():
            self.hideDescript.setChecked(True)
        self.displayEntries.clear()
        self.displayEntries.setRowCount(0)
        self.entryText.clear()
        index_name = self.indexChoice.currentText()
        if index_name not in self.index_dict:
            return
        self.indexPrefix.setText(self.index_dict[index_name]["prefix"])
        if self.index_dict[index_name]["hidden"] != self.hideDescript.isChecked():
            self.hideDescript.setChecked(self.index_dict[index_name]["hidden"])
        self.displayEntries.setRowCount(len(self.index_dict[index_name]["entries"]))
        self.displayEntries.setHorizontalHeaderLabels(["Name", "Description"])
        for row, (k, v) in enumerate(self.index_dict[index_name]["entries"].items()):
            key = QTableWidgetItem(k)
            key.setFlags(key.flags() & ~Qt.ItemIsEditable & ~ Qt.ItemIsUserCheckable)
            self.displayEntries.setItem(row, 0, key)
            self.displayEntries.setItem(row, 1, QTableWidgetItem(v))
    def save_index(self):
        index_name = self.indexChoice.currentText()
        prefix = self.indexPrefix.text()
        hidden = self.hideDescript.isChecked()
        entry_dict = {}
        for row in range(self.displayEntries.rowCount()):
            key = self.displayEntries.item(row, 0).text()
            description = self.displayEntries.item(row, 1).text()
            entry_dict[key] = description
        self.index_dict[index_name] = {"prefix": prefix, "hidden": hidden, "entries": entry_dict}
        self.updated_dict.emit()
    def new_index(self):
        count = self.indexChoice.count()
        self.indexChoice.addItem(str(count))
        self.update_display(count)
    def enable_add(self, index):
        if index > -1:
            self.entryAdd.setEnabled(True)
    def add_new_entry(self):
        index_name = self.indexChoice.currentText()
        new_entry = self.entryText.text()
        prefix = self.indexPrefix.text()
        if index_name not in self.index_dict:
            self.index_dict[index_name] = {"prefix": prefix, "hidden": True, "entries": {}}
        self.index_dict[index_name]["entries"][new_entry] = ""
        self.update_display(self.indexChoice.currentIndex())
    def enable_insert(self):
        if self.displayEntries.currentRow() > -1:
            self.saveAndInsert.setEnabled(True)
    def insert_entry(self):
        index_name = self.indexChoice.currentText()
        selected_row = self.displayEntries.currentRow()
        if selected_row == -1:
            return
        entry_text = self.displayEntries.item(selected_row, 0).text()
        index_dict = self.index_dict[index_name]
        el = index_text(prefix = index_dict["prefix"], indexname = index_name, description = index_dict["entries"][entry_text], hidden = index_dict["hidden"], text = entry_text)
        self.index_insert.emit(el)
        self.save_index()
    def update_dict(self, index_dict):
        self.index_dict = index_dict
        self.indexChoice.clear()
        self.indexChoice.addItems([*self.index_dict])
        if len(self.index_dict) > 0:
            self.update_display(0)
        else:
            self.update_display(-1)
