import importlib
from typing import Any
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtWidgets import QWidget, QDialog, QHBoxLayout, QTextBrowser, QTabWidget, QVBoxLayout, QToolBar
from PySide6.QtGui import QTextDocument, QAction
from PySide6 import QtHelp


class helpBrowser(QTextBrowser):
    def __init__(self, help_engine = None):
        super().__init__()
        if help_engine:
            self.help_engine = help_engine
    def loadResource(self, type, name):
        baseUrl = self.source()
        if name.isRelative():
            name = baseUrl.resolved(name)
        if name.scheme() == "qthelp":
            return self.help_engine.fileData(name)
        else:
            return super().loadResource(type, name)
    def load(self, url):
        self.setSource(url)
        self.setHtml(str(self.loadResource(QTextDocument.HtmlResource, url).data(), "utf-8"))

class helpDialogWindow(QDialog):
    """Display help documentation.
    """
    def __init__(self):
        super().__init__()
        help_path = (importlib.resources.files(__package__) / "data/plover2CAT.qhc")
        self.help_engine = QtHelp.QHelpEngine(str(help_path))
        self.help_engine.setupData()
        self.help_engine.registerDocumentation(str(help_path))
        self.search_engine = self.help_engine.searchEngine()
        self.content = self.help_engine.contentWidget()
        self.content_display = helpBrowser(self.help_engine)
        self.content_display.anchorClicked.connect(self.toc_go_to)
        self.content.linkActivated.connect(self.toc_go_to)
        self.search_input = self.search_engine.queryWidget()
        self.result_widget = self.search_engine.resultWidget()
        self.search_input.search.connect(self.load_search)
        self.result_widget.requestShowLink.connect(self.load_help)
        self.menu = QToolBar()
        self.browse_back = QAction("<")
        self.browse_back.setToolTip("Click to go back.")
        self.browse_back.triggered.connect(lambda: self.content_display.backward())
        self.content_display.backwardAvailable.connect(lambda stat: self.browse_back.setEnabled(stat))
        self.browse_forward = QAction(">")
        self.browse_forward.setToolTip("Click to go forward.")
        self.browse_forward.triggered.connect(lambda: self.content_display.forward())
        self.content_display.forwardAvailable.connect(lambda stat: self.browse_forward.setEnabled(stat))

        self.menu.addAction(self.browse_back)
        self.menu.addAction(self.browse_forward)
        
        self.content.linkActivated.connect(self.load_help)
        self.main_layout = QHBoxLayout()
        self.tab_widget = QTabWidget()

        content_layout = QVBoxLayout()
        content_layout.addWidget(self.menu)
        content_layout.addWidget(self.content)

        content_widget = QWidget()
        content_widget.setLayout(content_layout)

        search_layout = QVBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.result_widget)
        search_widget = QWidget()
        search_widget.setLayout(search_layout)
        
        self.tab_widget.addTab(content_widget, "Table of Contents")
        self.tab_widget.addTab(search_widget, "Search")

        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(self.content_display, 4)
        self.setLayout(self.main_layout)
        self.resize(600, 400)
        self.load_help(QUrl("qthelp://org.sphinx.plover2cat/doc/index.html"))

    def load_help(self, link):
        self.content_display.load(link)
        self.toc_go_to(link)
    
    def toc_go_to(self, link):
        toc_index = self.content.indexOf(link)
        self.content.setExpanded(toc_index, True)
        self.content.scrollTo(toc_index)

    def load_search(self):
        query = self.search_input.searchInput()
        self.search_engine.search(query)
        
