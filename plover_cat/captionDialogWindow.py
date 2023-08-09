from PyQt5.QtWidgets import QDialog, QFontDialog
from PyQt5.QtGui import QFont

from plover_cat.caption_dialog_ui import Ui_captionDialog

class captionDialogWindow(QDialog, Ui_captionDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.font = QFont("Courier New", 12)
        self.fontSelector.clicked.connect(self.set_font)
        self.fontSelector.setText(f"{self.font.family()} {self.font.pointSize()}")
    def set_font(self):
        font, ok = QFontDialog.getFont(self.font, self)
        if ok:
            self.font = font
            self.fontSelector.setText(f"{self.font.family()} {self.font.pointSize()}")