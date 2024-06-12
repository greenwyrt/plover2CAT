import unittest
import pathlib
from tempfile import mkdtemp, mkstemp
from shutil import rmtree
from io import StringIO
from unittest import TextTestRunner

from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QTextCursor
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke
from plover_cat.steno_objects import *
from plover_cat.TextEditor import PloverCATEditor
from plover_cat.test_dialog_ui import Ui_testDialog

class TestStenoData(unittest.TestCase):
    def test_text_element_creation(self):
        el = text_element(text = "abc")
        self.assertEqual(el.element, "text")
        self.assertEqual(el.to_text(), "abc")
        self.assertEqual(len(el), 3)
        self.assertEqual(el.length(), 3)
    def test_steno_element_creation(self):
        el = stroke_text(stroke = "T-", text = "it")
        self.assertEqual(el.element, "stroke")
        self.assertEqual(el.to_text(), "it")
        self.assertEqual(len(el), 2)
        self.assertEqual(el.length(), 2)
    def test_field_element_creation(self):
        el = text_field(name = "SPEAKER_STPHAO")
        val = "Mr. Stphao"
        self.assertEqual(el.element, "field")
        self.assertEqual(el.to_text(), val)
        self.assertEqual(len(el), len(val))
        self.assertEqual(el.length(), 1)
        self.assertNotEqual(el.length, len(val))
    def test_image_element(self):
        el = image_text()
        self.assertEqual(el.element, "image")
        self.assertEqual(len(el), 1)        
        self.assertEqual(el.length(), 1)                
    def test_automatic_element(self):
        txt = "ABC"
        affix_txt = "Q.\tABC?"
        el = automatic_text(prefix = "Q.\t", suffix = "?", stroke = "AEU", text = txt)
        self.assertEqual(el.element, "automatic")
        self.assertEqual(el.to_text(), affix_txt)
        self.assertNotEqual(len(el), len(txt))
        self.assertEqual(len(el), len(affix_txt))
        self.assertEqual(el.length(), len(txt))
        self.assertNotEqual(el.length(), len(affix_txt))
    def test_index_element(self):
        indices = {"0": {"prefix": "Exhibit", "hidden": True, "entries": {"A": " A glass.", "B": " Two glasses."}},
                     "1": {"prefix": "Index", "hidden": False, "entries": {"1": " The first.", "2": " The second."}}}
        index_name = "0"
        index_dict = indices[index_name]
        entry_text = "A"
        correct_txt = "Exhibit A"
        el = index_text(prefix = index_dict["prefix"], indexname = index_name, description = index_dict["entries"][entry_text], hidden = index_dict["hidden"], text = entry_text)
        self.assertEqual(el.element, "index")
        self.assertEqual(el.to_text(), correct_txt)
        self.assertEqual(len(el), len(correct_txt))
        self.assertNotEqual(len(el), 1)
        self.assertEqual(el.length(), 1)
        self.assertNotEqual(el.length(), len(correct_txt))
        index_name = "1"
        index_dict = indices[index_name]
        entry_text = "1"
        correct_txt = "Index 1 The first."
        el = index_text(prefix = index_dict["prefix"], indexname = index_name, description = index_dict["entries"][entry_text], hidden = index_dict["hidden"], text = entry_text)
        self.assertEqual(el.to_text(), correct_txt)
        self.assertEqual(len(el), len(correct_txt))
        self.assertNotEqual(len(el), 1)
        self.assertEqual(el.length(), 1)
        self.assertNotEqual(el.length(), len(correct_txt))
    def element_addition(self):
        el1 = text_element("ABC")
        el2 = text_element("DEF")
        res = el1 + el2 
        self.assertEqual(res.to_text(), "ABCDEF")
        el_stroke = stroke_text(stroke = "T-", text = " it")
        res = el1 + el_stroke
        self.assertEqual(res.to_text(), "ABC it")
        res = el_stroke + el1 
        self.assertEqual(res.to_text(), " itABC")
        self.assertEqual(res.stroke, "T-")
        el_stroke2 = stroke_text(stroke = "-B", text = "be")
        res = el_stroke + el_stroke2
        self.assertEqual(res.to_text(), " itbe")
        self.assertEqual(res.stroke, "T-/-B")
        with self.assertRaises(ValueError):
            el_stroke2 + el_stroke
        el_index = index_text(description = "index descript", text = " index name")
        with self.assertRaises(NotImplemented):
            el_stroke + el_index
            el_index + el_stroke
    def test_element_collection(self):
        stroke_data = [text_element(text = "ABC"),  
                        text_element(text = "2 ", time = "2000-01-23T00:00:00.111"), 
                        stroke_text(stroke = "EUFS", text = "I was ", time = "2100-01-24T00:00:00.111"), 
                        stroke_text(stroke = "TAO", text = "too "), 
                        index_text(description = "index descript", text = " index name")]
        sc = element_collection(stroke_data)
        self.assertEqual(sc.element_count(), 5)
        self.assertEqual(sc.stroke_count(), 2)
        self.assertEqual(sc.collection_time(), "2000-01-23T00:00:00.111")
        self.assertEqual(sc.collection_time(reverse = True), "2100-01-24T00:00:00.111")
        merged = sc.merge_elements()
        self.assertEqual(merged.element_count(), 4)
        sc.remove_steno(15, 16)
        self.assertEqual(sc.to_text(), "ABC2 I was too ")
        sc.remove_steno(3, 6)
        self.assertEqual(sc.to_text(), "ABC was too ")
        new_data = [text_element(text = "ABCD"), text_element(text = "123")]
        sc.insert_steno(4, element_collection(new_data))
        self.assertEqual(sc.to_text(), "ABC ABCD123was too ")

class TestTextEdit(unittest.TestCase):
    def __init__(self, testname, editor):
        super(TestTextEdit, self).__init__(testname)
        self.editor = editor
        self.temp_dir = None
    def setUp(self):
        self.temp_dir = mkdtemp()
    def tearDown(self):
        self.editor.textEdit.undo_stack.setClean()
        self.editor.close_file()
        rmtree(self.temp_dir)
    def testMonolithic(self):
        for _s in ["step_Open", "step_ConfirmFiles", "step_Stroke"]:
            try:
                getattr(self, _s)()
            except Exception as e:
                self.fail('{} failed({})'.format(_s, e))   
    def step_Open(self):
        file_path = pathlib.Path(self.temp_dir) / "test"
        self.editor.open_file(file_path)
    def step_ConfirmFiles(self):
        engine_dicts = self.editor.engine.config["dictionaries"]
        default_dict_dir = self.editor.textEdit.file_name / "dict"
        self.assertTrue(default_dict_dir.exists())
        default_dict = default_dict_dir / "default.json"
        self.assertTrue(default_dict.exists())
        style_file = self.editor.textEdit.file_name / "styles" / "default.json"
        self.assertTrue(style_file.exists())
    def step_Stroke(self):
        engine_state = self.editor.engine.output
        self.editor.engine.set_output(True)
        self.editor.engine.clear_translator_state()
        # test append
        self.editor.on_send_string("THE")
        self.assertEqual(self.editor.textEdit.last_string_sent, "THE")
        self.editor.textEdit.on_stroke(Stroke("-T"))
        self.assertEqual(self.editor.textEdit.toPlainText().strip(), "THE")
        stroke_data = self.editor.textEdit.textCursor().block().userData()["strokes"]
        self.assertEqual(stroke_data.element_count(), 1)
        # test delete
        self.editor.count_backspaces(3)
        self.editor.textEdit.on_stroke(Stroke("*"))
        self.assertEqual(self.editor.textEdit.toPlainText(), "")
        self.assertEqual(stroke_data.element_count(), 0)
        # test log
        self.editor.textEdit.log_to_tape(Stroke("*"))
        self.assertFalse(len(self.editor.strokeList.toPlainText()), 0)
        self.editor.engine.set_output(engine_state)
    def step_AddDict(self):
        new_dict = mkstemp()
        new_dict_contents = {"-T": "Success"}
        save_json(new_dict_contents, new_dict)
        self.editor.add_dict(new_dict)
        engine_state = self.editor.engine.output
        self.editor.engine.set_output(True)
        self.editor.engine.clear_translator_state()
        self.editor.textEdit.on_stroke(Stroke("-T"))
        self.assertEqual(self.editor.textEdit.toPlainText().strip(), "Success")
        self.editor.engine.set_output(engine_state)
class testDialogWindow(QDialog, Ui_testDialog):
    """Dialog to run selected tests for editor and transcript.
    """
    def __init__(self, editor):
        super().__init__()
        self.setupUi(self)
        self.editor = editor
        self.runTest.clicked.connect(self.run_tests)
    def display_log(self):
        log_path = pathlib.Path(CONFIG_DIR) / "plover.log"
        log_contents = log_path.read_text()
        self.output.clear()
        self.output.setPlainText(log_contents)
        self.output.moveCursor(QTextCursor.End)
    def run_tests(self):
        res_output = StringIO()
        suite_steno = unittest.TestLoader().loadTestsFromTestCase(TestStenoData)
        suite = unittest.TestSuite([suite_steno])
        suite.addTest(TestTextEdit("testMonolithic", self.editor))
        # suite.addTest(TestTextEdit("testConfirmFiles", self.editor))
        res = TextTestRunner(stream = res_output, verbosity=1).run(suite)
        self.output.clear()
        self.output.setPlainText(res_output.getvalue())
