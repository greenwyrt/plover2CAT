
from plover_cat.affix_dialog_ui import Ui_affixDialog
from PyQt5.QtWidgets import QDialog
from copy import deepcopy

class affixDialogWindow(QDialog, Ui_affixDialog):
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
        if self.prefixString.hasFocus():
            txt = self.prefixString.text()
            self.prefixString.insert("\t")
        if self.suffixString.hasFocus():
            txt = self.suffixString.text()
            self.suffixString.insert("\t")
    def store_affix(self):
        par_dict = {}
        if self.prefixString.text():
            par_dict["prefix"] = self.prefixString.text()
        if self.suffixString.text():
            par_dict["suffix"] = self.suffixString.text()
        if par_dict:
            self.affix_dict[self.styleName.currentText()] = par_dict