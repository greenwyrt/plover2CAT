from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout

from plover.gui_qt.tool import Tool

from plover_cat.plover_cat_ui import Ui_PloverCAT

from plover_cat.PloverCATWindow import PloverCATWindow

from . __version__ import __version__

class PloverCAT(Tool):

    TITLE = "Plover2CAT"
    ROLE = "plover2cat"
    ICON = ':/resources/icon.svg'
    SHORTCUT = "Ctrl+P"

    def __init__(self, engine):
        super().__init__(engine)
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint)
        self.layout = QHBoxLayout()
        self.everything = PloverCATWindow(engine)
        self.layout.addWidget(self.everything)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        #what does this do?
        self.finished.connect(lambda: None)
    def reject(self):
        pass

