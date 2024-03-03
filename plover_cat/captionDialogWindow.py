from PyQt5.QtWidgets import QDialog, QFontDialog
from PyQt5.QtGui import QFont

from plover_cat.caption_dialog_ui import Ui_captionDialog

class captionDialogWindow(QDialog, Ui_captionDialog):
    def __init__(self):
        """Set up configuration for captioning. 
        The fields for word buffer, caption length and max lines displayed
        have default values. Caption font is selected through a QFontDialog.
        Based on the endpoint selected, URL, Port and Password fields are 
        enabled and disabled. The settings are fed into ``captionWorker``.

        .. note:: 
            The value set in word buffer is special as it remains outside 
                of ``captionWorker``.
        """
        super().__init__()
        self.setupUi(self)
        self.font = QFont("Courier New", 12)
        """QFont: default for caption display"""
        self.fontSelector.clicked.connect(self.set_font)
        self.fontSelector.setText(f"{self.font.family()} {self.font.pointSize()}")
        self.remoteCapHost.activated.connect(self.enable_host_ui)
    def enable_host_ui(self, index):
        """Enable and disable related fields for endpoints.
        Supported endpoints: `None`, Microsoft Teams (untested), Zoom (untested),
        OBS for twitch (tested).  Teams and Zoom both require at least an URL. 
        OBS requires a local port and password. See how-to page for details.
        """
        if index != 0:
            self.hostURL.setEnabled(True)
            self.hostURL.setPlaceholderText("")
            self.serverPassword.setEnabled(False) 
            self.serverPort.setEnabled(False)
            self.serverPort.setPlaceholderText("")
            if index == 3:
                if not self.serverPort.text():
                    self.serverPort.setPlaceholderText("4455")
                if not self.hostURL.text():
                    self.hostURL.setPlaceholderText("localhost")
                self.serverPort.setEnabled(True)
                self.serverPassword.setEnabled(True)
        else:
            self.hostURL.setEnabled(False)
            self.serverPort.setEnabled(False)
            self.serverPort.setPlaceholderText("")
            self.serverPassword.setEnabled(False)                       
    def set_font(self):
        """Set font for display in caption window.
        """
        font, ok = QFontDialog.getFont(self.font, self)
        if ok:
            self.font = font
            self.fontSelector.setText(f"{self.font.family()} {self.font.pointSize()}")