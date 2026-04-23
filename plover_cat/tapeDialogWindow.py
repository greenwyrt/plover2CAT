from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QListWidgetItem
from PySide6.QtCore import Qt, Signal
import pathlib
from plover_cat.tape_dialog_ui import Ui_tapeDialog
from plover.steno import Stroke, normalize_stroke
from plover import system

class tapeDialogWindow(QDialog, Ui_tapeDialog):
    """Set up configuration for translating from tape
    """
    translate_stroke_from_tape = Signal(int)
    """Signal sent for translate, int being index at start"""
    undo_from_tape = Signal()
    """Signal sent to trigger undo of last stroke"""
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.paper_format = None
        self.tape_data = []
        self.select_tape.clicked.connect(self.load_tape)
        # self.tape_view.setUniformItemSizes(True)
        # self.tape_view.setLayoutMode(QListView.LayoutMode.Batched)
        self.translate.clicked.connect(lambda: self.signal_stroke())
        self.translate_ten.clicked.connect(lambda: self.signal_stroke(10))
        self.translate_all.clicked.connect(lambda: self.signal_stroke_all())
        self.undo_last.clicked.connect(lambda: self.signal_undo())

    def signal_undo(self):
        self.undo_from_tape.emit()
        current = self.tape_view.currentRow()
        self.tape_view.setCurrentRow(current - 1)

    def signal_stroke(self, strokes = 1):
        current = self.tape_view.currentRow()
        if current == -1:
            return
        min(current + strokes, self.tape_view.count() - 1)
        self.translate_stroke_from_tape.emit(strokes)
        self.tape_view.setCurrentRow(current + strokes)
        print(current)

    def signal_stroke_all(self):
        current = self.tape_view.currentRow()
        if current == -1:
            return
        self.translate_stroke_from_tape.emit(self.tape_view.count() - current + 1)
        self.tape_view.setCurrentRow(self.tape_view.count() - 1)

    def load_tape(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            "Select tape file to translate",
            "", "Tape (*.tape *.txt)")[0]
        if not selected_file:
            return
        selected_file = pathlib.Path(selected_file)
        self.select_tape.setText(selected_file.stem)   
        paper_format, ok = QInputDialog.getItem(
            self,
            "Translate Tape",
            "Format of tape file:",
            ["Plover2CAT", "Plover (raw)", "Plover (paper)"],
            editable=False,
        )
        if not ok:
            return
        self.tape_data = []
        self.paper_format = paper_format
        match paper_format:
            case "Plover (raw)":
                self.load_raw_paper(selected_file)
            case "Plover2CAT":
                self.load_plover2cat(selected_file)
            case "Plover (paper)":
                self.load_plover_paper(selected_file)
        self.pop_view()

    def load_raw_paper(self, file_path):
        with open(file_path) as f:
            for line in f:
                stroke = line
                self.tape_data.append(stroke)

    def load_plover2cat(self, file_path):
        with open(file_path) as f:
            for line in f:
                stroke = line.strip().split("|")[3]
                self.tape_data.append(stroke)              

    def load_plover_paper(self, file_path):
        with open(file_path) as f:
            for line in f:
                self.tape_data.append(line) 

    def pop_view(self):
        for stroke in self.tape_data:
            item = QListWidgetItem()
            item.setText(stroke)
            item.setData(Qt.UserRole, stroke)
            self.tape_view.addItem(item)
        self.tape_view.setCurrentRow(0)