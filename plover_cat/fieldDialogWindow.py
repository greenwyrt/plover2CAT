from copy import deepcopy
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtWidgets import QDialog
from plover_cat.field_dialog_ui import Ui_fieldDialog

class fieldDialogWindow(QDialog, Ui_fieldDialog):
    """Create, save and edit field values.
    
    The field editor is a modeal dialog opened through the menu. 
    Each field has an unique name and value. Fields are inserted
    into the transcript text by name and their value is displayed.
    
    :param user_field_dict: dict of {name: value}
    :type user_field_dict: dict, required
    :return: QDialog status code inherited from the QDialog class.
        Editor will access ``affix_dict`` from instance.
    :rtype: QDialog.DialogCode, either Accepted or Rejected         
    """
    def __init__(self, user_field_dict):
        super().__init__()
        self.setupUi(self)
        self.user_field_dict = deepcopy(user_field_dict)
        self.addNewField.clicked.connect(self.new_field)
        self.removeField.clicked.connect(self.remove_field)
        self.userDictTable.clearContents()
        self.userDictTable.setColumnCount(2)
        self.userDictTable.setHorizontalHeaderLabels(["Name", "Value"])
        self.userDictTable.setRowCount(len(self.user_field_dict))
        for row, (k, v) in enumerate(self.user_field_dict.items()):
            key = QTableWidgetItem(k)
            key.setFlags(key.flags() & ~Qt.ItemIsEditable & ~ Qt.ItemIsUserCheckable)
            self.userDictTable.setItem(row, 0, key)
            self.userDictTable.setItem(row, 1, QTableWidgetItem(v))
        self.userDictTable.cellChanged.connect(self.update_cell)
    def update_cell(self, row, col):
        """Update underlying field dict based on the cell changed."""
        key = self.userDictTable.item(row, 0).text()
        val = self.userDictTable.item(row, 1).text()
        self.user_field_dict[key] = val
    def new_field(self):
        """Add new field to field dict."""
        if self.fieldName.text().strip(" ") == "":
            return
        else:
            self.userDictTable.blockSignals(True)
            rows = self.userDictTable.rowCount()
            self.userDictTable.setRowCount(rows + 1)
            key = QTableWidgetItem(self.fieldName.text())
            key.setFlags(key.flags() & ~Qt.ItemIsEditable & ~ Qt.ItemIsUserCheckable)
            self.userDictTable.setItem(rows, 0, key)
            self.userDictTable.setItem(rows, 1, QTableWidgetItem(self.fieldValue.text()))
            self.user_field_dict[self.fieldName.text()] = self.fieldValue.text()
            self.userDictTable.blockSignals(False)
    def remove_field(self):
        """Delete field from field dict by deleting key:value pair."""
        select_item = self.userDictTable.selectedItems()
        if select_item:
            row = select_item[0].row()
            selected_key = self.userDictTable.item(row, 0).text()
            self.userDictTable.removeRow(row)
            self.user_field_dict.pop(selected_key, None)
