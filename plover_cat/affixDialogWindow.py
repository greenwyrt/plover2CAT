from plover_cat.affix_dialog_ui import Ui_affixDialog
from PySide6.QtWidgets import QDialog
from copy import deepcopy

class affixDialogWindow(QDialog, Ui_affixDialog):
    """Create, save and edit paragraph affixes for editor. 
    The affix editor dialog is a modal dialog opened through the menu.
    Text strings are added before and after each paragraph based
    on the style of each paragraph. The affix data is stored as 
    ``auto_paragraph_affixes`` in the config.
    
    :param affix_dict: dict of dicts of the form 
        ``{"Style": {"prefix": str, "suffix": str}}``
    :type affix_dict: dict, can be empty, required
    :param style_names: style names from style file
    :type style_names: list, required
    :return: QDialog status code inherited from the QDialog class.
        Editor will access ``affix_dict`` from instance.
    :rtype: QDialog.DialogCode, either Accepted or Rejected 
    """    
    def __init__(self, affix_dict, style_names):
        super().__init__()
        self.setupUi(self)
        self.affix_dict = deepcopy(affix_dict)
        self.styleName.addItems(style_names)
        self.styleName.setCurrentIndex(-1)
        self.styleName.activated.connect(self.display_affix)
        self.insertTab.clicked.connect(self.insert_tab)
        self.saveAffixes.clicked.connect(self.store_affix)
    def display_affix(self):
        """Display saved affixes for present style for editing"""
        current_style = self.styleName.currentText()
        if current_style in self.affix_dict and "prefix" in self.affix_dict[current_style]:
            self.prefixString.setText(self.affix_dict[current_style]["prefix"])
        else:
            self.prefixString.clear()
        if current_style in self.affix_dict and "suffix" in self.affix_dict[current_style]:    
            self.suffixString.setText(self.affix_dict[current_style]["suffix"])
        else:
            self.suffixString.clear()
    def insert_tab(self):
        """Insert tab character into affix field QLineedit"""
        if self.prefixString.hasFocus():
            txt = self.prefixString.text()
            self.prefixString.insert("\t")
        if self.suffixString.hasFocus():
            txt = self.suffixString.text()
            self.suffixString.insert("\t")
    def store_affix(self):
        """Saves affix strings from fields into ``affix_dict``"""
        par_dict = {}
        if self.prefixString.text():
            par_dict["prefix"] = self.prefixString.text()
        if self.suffixString.text():
            par_dict["suffix"] = self.suffixString.text()
        if par_dict:
            self.affix_dict[self.styleName.currentText()] = par_dict