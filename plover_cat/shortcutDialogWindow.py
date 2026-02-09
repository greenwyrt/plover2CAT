from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtGui import QKeySequence
from plover_cat.shortcut_dialog_ui import Ui_shortcutDialog

class shortcutDialogWindow(QDialog, Ui_shortcutDialog):
    """Set shortcuts for menu items in editor through the modal dialog.

    :param shortcut_dict: existing dict of shortcuts, {action: "str of keys"}
    :type shortcut_dict: dict
    :param menu_names: visible text of QAction objects in menus
    :type menu_names: list
    :param action_names: object names of QAction objects in menus
    :type action_names: list
    """
    def __init__(self, shortcut_dict, menu_names, action_names):
        super().__init__()
        self.setupUi(self)
        self.shortcut_dict = shortcut_dict
        self.menu_names = menu_names
        self.action_names = action_names
        self.text_name.clear()
        for menu, action in zip(self.menu_names, self.action_names):
            self.text_name.addItem(menu, action)
        if self.text_name.currentText():
            self.display_shortcut(self.text_name.currentIndex())
        self.validate.clicked.connect(self.check_save_shortcut)
        self.text_name.activated.connect(self.display_shortcut)          
    def display_shortcut(self, index):
        """Display existing shortcut, if set, of selected menu item"""
        self.shortcut.clear()
        self.text_name.setCurrentIndex(index)
        action = self.text_name.currentData()
        if action in self.shortcut_dict:
            keys = QKeySequence(self.shortcut_dict[action])
            self.shortcut.setKeySequence(keys)
    def check_save_shortcut(self):
        """Check if shortcut displayed is valid"""
        action = self.text_name.currentData()
        if not action:
            return
        keys = self.shortcut.keySequence().toString()
        if keys in self.shortcut_dict.values():
            QMessageBox.warning(self, "Plover2CAT", "This shortcut is already in use. Choose another one.")
            return
        reserved_keys = [f"Ctrl+{i}" for i in range(0,10)] + [f"Ctrl+Shift+{i}" for i in range(0,10)] 
        if keys in reserved_keys:
            QMessageBox.warning(self, "Plover2CAT", "This shortcut is a reserved shortcut. Choose another one.")
            return
        self.shortcut_dict[action] = keys