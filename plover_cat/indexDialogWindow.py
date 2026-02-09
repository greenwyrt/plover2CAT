from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTableWidgetItem, QDialog
from plover_cat.index_dialog_ui import Ui_indexDialog
from plover_cat.steno_objects import index_text

class indexDialogWindow(QDialog, Ui_indexDialog):
    """Create, save and edit index entries for editor.

    The index editor dialog is a non-modal dialog opened through the menu.
    Index entries are numbered, and have a description that can be hidden.
    Index entries have to belong to an index with a prefix string, and there 
    can be multiple indices.

    :param index_dict: dict with {index_name: {prefix: str, hidden: bool, entries: {name: description, ...}}, ..}
    :type index_dict: dict    
    """
    index_insert = Signal(object)
    """Signal emitted when user has selected an entry to insert into text"""
    updated_dict = Signal()
    """Signal emitted when the index dictionary has been updated"""
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
        """Display existing entries for selected index."""
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
        """Save selected index."""
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
        """Create new index."""
        count = self.indexChoice.count()
        self.indexChoice.addItem(str(count))
        self.update_display(count)
    def enable_add(self, index):
        """Allow new entry to be added if index is selected."""
        if index > -1:
            self.entryAdd.setEnabled(True)
    def add_new_entry(self):
        """Add new entry to currently selected index."""
        index_name = self.indexChoice.currentText()
        new_entry = self.entryText.text()
        prefix = self.indexPrefix.text()
        if index_name not in self.index_dict:
            self.index_dict[index_name] = {"prefix": prefix, "hidden": True, "entries": {}}
        self.index_dict[index_name]["entries"][new_entry] = ""
        self.update_display(self.indexChoice.currentIndex())
    def enable_insert(self):
        """Allow insert into text if an entry is selected."""
        if self.displayEntries.currentRow() > -1:
            self.saveAndInsert.setEnabled(True)
    def insert_entry(self):
        """Insert selected entry into text"""
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
        """Update existing index dict, used when indices are gathered from transcript """
        self.index_dict = index_dict
        self.indexChoice.clear()
        self.indexChoice.addItems([*self.index_dict])
        if len(self.index_dict) > 0:
            self.update_display(0)
        else:
            self.update_display(-1)
