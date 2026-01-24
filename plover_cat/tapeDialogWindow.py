from PySide6.QtWidgets import QDialog, QFileDialog, QInputDialog, QListView
from PySide6.QtGui import QStandardItem, QStandardItemModel
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
        self.tape_data = []
        self.select_tape.clicked.connect(self.load_tape)
        self.tape_view.setUniformItemSizes(True)
        self.tape_view.setLayoutMode(QListView.LayoutMode.Batched)
        self.translate.clicked.connect(lambda: self.signal_stroke())
        self.translate_ten.clicked.connect(lambda: self.signal_stroke(10))
        self.translate_all.clicked.connect(lambda: self.signal_stroke_all())
        self.undo_last.clicked.connect(lambda: self.signal_undo())

    def signal_undo(self):
        self.undo_from_tape.emit()
        current = self.tape_view.currentIndex().row()
        self.tape_view.setCurrentIndex(current - 1)

    def signal_stroke(self, strokes = 1):
        self.translate_stroke_from_tape.emit(strokes)
        current = self.tape_view.currentIndex().row()
        self.tape_view.setCurrentIndex(current + strokes)

    def signal_stroke_all(self):
        current = self.tape_view.currentIndex().row()
        self.translate_stroke_from_tape.emit(self.tape_model.rowCount() - current + 1)

    def load_tape(self):
        selected_file = QFileDialog.getOpenFileName(
            self,
            "Select tape file to translate",
            "", "Tape (*.tape *.txt)")[0]
        if not selected_file:
            return
        selected_file = pathlib.Path(selected_file)
        self.select_tape.setText(selected_file.stem)   
        paper_format, ok = QInputDialog.getItem(self, "Translate Tape", "Format of tape file:", ["Plover2CAT", "Plover (raw)", "Plover (paper)"], editable = False)
        if not ok:
            return
        self.tape_data = []
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
                stroke = Stroke(normalize_stroke(line.strip().replace(" ", "")))
                self.tape_data.append(stroke.rtfcre)

    def load_plover2cat(self, file_path):
        with open(file_path) as f:
            for line in f:
                stroke_contents = line.strip().split("|")[3]
                keys = []
                for i in range(len(stroke_contents)):
                    if not stroke_contents[i].isspace() and i < len(system.KEYS):
                        keys.append(system.KEYS[i])
                self.tape_data.append(Stroke(keys).rtfcre)              

    def load_plover_paper(self, file_path):
        with open(file_path) as f:
            for line in f:
                keys = []
                for i in range(len(line)):
                    if not line[i].isspace() and i < len(system.KEYS):
                        keys.append(system.KEYS[i])   
                self.tape_data.append(Stroke(keys).rtfcre) 

    def pop_view(self):
        self.tape_model = QStandardItemModel(self)
        for stroke in self.tape_data:
            item = QStandardItem()
            item.setText(stroke)
            item.setData(stroke, Qt.UserRole)
            self.tape_model.appendRow(item)
        self.tape_view.setModel(self.tape_model)