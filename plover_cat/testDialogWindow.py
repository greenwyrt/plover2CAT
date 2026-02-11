import unittest
import pathlib
import os
from tempfile import mkdtemp, mkstemp
from shutil import rmtree
from io import StringIO
from unittest import TextTestRunner

from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtCore import Qt, QSettings
from plover.oslayer.config import CONFIG_DIR
from plover.steno import Stroke
from plover_cat.helpers import save_json
from plover_cat.steno_objects import text_element, stroke_text, text_field, image_text, automatic_text, index_text, element_collection
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
        correct_txt = "Exhibit\u00a0A"
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
        correct_txt = "Index\u00a01 The first."
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
                        stroke_text(stroke = "EUFS", text = "I was ", time = "2100-01-24T00:00:00.111", audiotime = "00:00:01.123"), 
                        stroke_text(stroke = "TAO", text = "too ", audiotime = "00:00:05.567"), 
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
        self.assertEqual(sc.closest_audiotime_at_pos(3), "")
        self.assertEqual(sc.closest_audiotime_at_pos(7), "00:00:01.123")
        self.assertEqual(sc.closest_audiotime_at_pos(9), "00:00:01.123")
        self.assertEqual(sc.closest_audiotime_at_pos(11), "00:00:01.123")
        self.assertEqual(sc.closest_audiotime_at_pos(13), "00:00:01.123")
        self.assertEqual(sc.closest_audiotime_at_pos(17), "00:00:01.123")

class TestTextEdit(unittest.TestCase):
    def __init__(self, testname, editor, selection):
        super(TestTextEdit, self).__init__(testname)
        self.editor = editor
        self.temp_dir = None
        self.output_setting = False
        self.space_setting = "Before Output"
        self.selection = selection
    def setUp(self):
        self.temp_dir = mkdtemp()
        self.output_setting = self.editor.engine.output
        self.editor.engine.set_output(True)
        self.space_setting = self.editor.engine.config["space_placement"]
        self.editor.engine.config["space_placement"] = "Before Output"
        self.step_Open()
    def tearDown(self):
        self.editor.engine.set_output(self.output_setting)
        self.editor.engine.config["space_placement"] = self.space_setting
        self.editor.textEdit.undo_stack.setClean()
        self.editor.close_file()
        rmtree(self.temp_dir)
    def testMonolithic(self):
        for _s in self.selection:
            try:
                getattr(self, _s)()
            except Exception as e:
                self.fail('{} failed({})'.format(_s, e))   
    def step_Open(self):
        file_path = pathlib.Path(self.temp_dir) / "test"
        self.editor.open_file(file_path)
    def step_ConfirmFiles(self):
        default_dict_dir = self.editor.textEdit.file_name / "dict"
        self.assertTrue(default_dict_dir.exists())
        default_dict = default_dict_dir / "default.json"
        self.assertTrue(default_dict.exists())
        style_file = self.editor.textEdit.file_name / "styles" / "default.json"
        self.assertTrue(style_file.exists())
    def step_Stroke(self):
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
        self.assertNotEqual(len(self.editor.strokeList.toPlainText()), 0)
        self.editor.textEdit.clear_transcript()
    def step_WriteTwoLine(self):
        # todo: create mock tape to read instead
        self.editor.on_send_string("ABC\\nDEF")
        self.editor.textEdit.on_stroke(Stroke("S"))
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC\\nDEF")
        self.editor.textEdit.clear_transcript()        
    def step_AddRemoveDict(self):
        dict_dir = self.editor.textEdit.file_name / "dict"
        handle, new_dict = mkstemp(suffix = ".json")
        new_dict_contents = {"S": "Success"}
        save_json(new_dict_contents, new_dict)
        self.editor.add_dict(new_dict)
        self.assertEqual(len([p for p in dict_dir.iterdir() if p.suffix == ".json"]), 2)
        self.assertEqual(self.editor.engine.lookup(tuple("S")), "Success")
        new_dict_path = dict_dir / pathlib.Path(new_dict).name
        self.editor.remove_dict(new_dict_path)
        self.assertEqual(len([p for p in dict_dir.iterdir() if p.suffix == ".json"]), 2)
        self.assertNotEqual(self.editor.engine.lookup(tuple("S")), "Success")
        os.close(handle)
        pathlib.Path(new_dict).unlink()
    def step_SplitPar(self):
        one_text = {0: {"style": "Normal", "strokes": [{"data": "ABCDEF", "element": "stroke", "stroke": "S-", "time": "2000-01-01T00:00:00.001"}]}}
        self.editor.textEdit.undo_stack.setClean()
        save_json(one_text, self.editor.textEdit.file_name.joinpath(self.editor.textEdit.file_name.stem).with_suffix(".transcript"))
        self.editor.close_file()
        self.editor.open_file(pathlib.Path(self.temp_dir) / "test")
        cursor = self.editor.textEdit.textCursor()
        cursor.setPosition(3)
        self.editor.textEdit.setTextCursor(cursor)
        self.editor.textEdit.split_paragraph()
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC\nDEF")
        self.editor.textEdit.undo_stack.undo()
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABCDEF")
        stroke_data = self.editor.textEdit.textCursor().block().userData()["strokes"]
        self.assertEqual(len(stroke_data.data), 1)
    def step_SplitParSpace(self):
        one_text = {0: {"style": "Normal", "strokes": [{"data": "ABC DEF", "element": "stroke", "stroke": "S-", "time": "2000-01-01T00:00:00.001"}]}}
        self.editor.textEdit.undo_stack.setClean()
        save_json(one_text, self.editor.textEdit.file_name.joinpath(self.editor.textEdit.file_name.stem).with_suffix(".transcript"))
        self.editor.close_file()
        self.editor.open_file(pathlib.Path(self.temp_dir) / "test")
        cursor = self.editor.textEdit.textCursor()
        cursor.setPosition(3)
        self.editor.textEdit.setTextCursor(cursor)
        self.editor.textEdit.split_paragraph()
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC\nDEF")
        self.editor.textEdit.undo_stack.undo()
        cursor.setPosition(3)
        self.editor.textEdit.setTextCursor(cursor)
        self.editor.textEdit.split_paragraph(remove_space = False)
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC\n DEF")
    def step_MergePar(self):
        one_text = {0: {"style": "Normal", "strokes": [{"data": "ABC", "element": "stroke", "stroke": "S-", "time": "2000-01-01T00:00:00.001"},
                                                         {"data": "\n", "element": "stroke", "stroke": "R-R", "time": "2000-01-01T00:00:00.002"}]},
                    1: {"style": "Normal", "strokes": [{"data": "DEF", "element": "stroke", "stroke": "-T", "time": "2000-01-01T00:00:00.002"}]}}
        self.editor.textEdit.undo_stack.setClean()
        save_json(one_text, self.editor.textEdit.file_name.joinpath(self.editor.textEdit.file_name.stem).with_suffix(".transcript"))
        self.editor.close_file()
        self.editor.open_file(pathlib.Path(self.temp_dir) / "test")  
        cursor = self.editor.textEdit.textCursor()
        cursor.setPosition(3)
        self.editor.textEdit.setTextCursor(cursor)
        self.editor.textEdit.merge_paragraphs()   
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC\nDEF")
        cursor.setPosition(5) 
        self.editor.textEdit.setTextCursor(cursor)
        self.editor.textEdit.merge_paragraphs()
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC DEF")
        self.editor.textEdit.undo_stack.undo()
        self.assertEqual(self.editor.textEdit.toPlainText(), "ABC\nDEF")
    def step_CheckStyleAttr(self):
        one_text = {0: {"style": "Normal", "strokes": [{"data": "ABC", "element": "stroke", "stroke": "S-", "time": "2000-01-01T00:00:00.001"},
                                                         {"data": "\n", "element": "stroke", "stroke": "R-R", "time": "2000-01-01T00:00:00.002"}]},
                    1: {"style": "Question", "strokes": [{"data": "DEF", "element": "stroke", "stroke": "-T", "time": "2000-01-01T00:00:00.002"}]}}
        self.editor.textEdit.undo_stack.setClean()
        save_json(one_text, self.editor.textEdit.file_name.joinpath(self.editor.textEdit.file_name.stem).with_suffix(".transcript"))
        self.editor.close_file()
        self.editor.open_file(pathlib.Path(self.temp_dir) / "test")  
        cursor = self.editor.textEdit.textCursor()
        cursor.setPosition(2)
        self.assertEqual(cursor.block().userData()["style"], "Normal")
        cursor.setPosition(5)
        self.assertEqual(cursor.block().userData()["style"], "Question")
    def step_ChangeStyle(self):
        one_text = {0: {"style": "Normal", "strokes": [{"data": "ABC", "element": "stroke", "stroke": "S-", "time": "2000-01-01T00:00:00.001"},
                                                         {"data": "\n", "element": "stroke", "stroke": "R-R", "time": "2000-01-01T00:00:00.002"}]},
                    1: {"style": "Question", "strokes": [{"data": "DEF", "element": "stroke", "stroke": "-T", "time": "2000-01-01T00:00:00.002"}]}}
        self.editor.textEdit.undo_stack.setClean()
        save_json(one_text, self.editor.textEdit.file_name.joinpath(self.editor.textEdit.file_name.stem).with_suffix(".transcript"))
        self.editor.close_file()
        self.editor.open_file(pathlib.Path(self.temp_dir) / "test")  
        cursor = self.editor.textEdit.textCursor()
        cursor.setPosition(5)
        self.editor.textEdit.setTextCursor(cursor)
        self.editor.textEdit.set_paragraph_style("Normal")
        self.assertEqual(cursor.block().blockFormat().textIndent(), 0)
        self.editor.textEdit.set_paragraph_style("Question")
        self.assertEqual(cursor.block().blockFormat().textIndent(), 0.5 * 96)
        tabs = [tab.position for tab in cursor.block().blockFormat().tabPositions()]
        self.assertEqual(96 in tabs, True)
    def step_ColorHighlight(self):
        one_text = {0: {"style": "Normal", "strokes": [{"data": "ABC", "element": "stroke", "stroke": "S-", "time": "2000-01-01T00:00:00.001"},
                                                         {"data": "\n", "element": "stroke", "stroke": "R-R", "time": "2000-01-01T00:00:00.002"}]},
                    1: {"style": "Question", "strokes": [{"data": "DEF", "element": "text", "time": "2000-01-01T00:00:00.002"}]}}
        self.editor.textEdit.undo_stack.setClean()
        save_json(one_text, self.editor.textEdit.file_name.joinpath(self.editor.textEdit.file_name.stem).with_suffix(".transcript"))
        self.editor.close_file()        
        settings = QSettings("Plover2CAT-4", "OpenCAT")
        old_color = settings.value("stroke", "black")
        new_color = QColor("blue")
        QSettings("Plover2CAT-4", "OpenCAT").setValue("colorStroke", new_color)
        self.editor.open_file(pathlib.Path(self.temp_dir) / "test")
        self.editor.update_highlight_color()
        self.editor.textEdit.get_highlight_colors()
        self.editor.refresh_editor_styles()
        cursor = self.editor.textEdit.textCursor()   
        cursor.setPosition(1)
        self.assertEqual(cursor.charFormat().foreground().color(), new_color)
        settings.setValue("stroke", old_color) 
    def step_loadNewStyle(self):
        pass      
    def step_SwitchTranscriptsPage(self):
        #change style param
        self.editor.page_max_lines.setValue(20)
        self.editor.textEdit.set_config_value("page_max_line", 20)
        config = self.editor.textEdit.config  
        self.assertEqual(config["page_max_line"], 20)        
        # open second transcript, make sure style param is default
        sec = pathlib.Path(self.temp_dir) / "style_default"
        self.editor.open_file(sec) 
        self.assertNotEqual(self.editor.page_max_lines.value(), 20)
        current_index_tab = self.editor.mainTabs.currentIndex()
        self.editor.switch_restore(current_index_tab - 1)
        config = self.editor.textEdit.config  
        self.assertEqual(config["page_max_line"], 20)                    
        self.assertEqual(self.editor.page_max_lines.value(), 20)
        self.editor.textEdit.undo_stack.setClean()
        self.editor.close_file()     
    def step_SwitchTranscripts(self):
        #change style param and mock click to set 
        self.editor.blockFontUnderline.setChecked(True)
        self.editor.style_edit()
        print(self.editor.textEdit.styles)      
        # open second transcript, make sure style param is default
        sec = pathlib.Path(self.temp_dir) / "style_default"
        self.editor.open_file(sec)
        self.editor.update_gui()
        print(self.editor.textEdit.styles)
        cursor = self.editor.textEdit.textCursor() 
        cursor.insertText("user action")  
        cursor.setPosition(0)        
        self.assertEqual(self.editor.blockFontUnderline.isChecked(), False)
        # # switch to first transcript, make sure style param is back to changed
        current_index_tab = self.editor.mainTabs.currentIndex()
        self.editor.switch_restore(current_index_tab - 1)
        cursor = self.editor.textEdit.textCursor()   
        cursor.setPosition(0)        
        self.assertTrue(self.editor.blockFontUnderline.isChecked())
        # not working
    def step_insertText(self):
        self.editor.textEdit.clear_transcript()
        self.editor.insert_text("This is one line.")
        self.assertEqual(self.editor.textEdit.toPlainText(), "This is one line.")
        self.editor.textEdit.clear_transcript()
        self.editor.textEdit.insert_text(["This is one line.", "This is the second."])
        self.assertEqual(self.editor.textEdit.toPlainText(), "This is one line.\nThis is the second.")
        self.editor.textEdit.clear_transcript()
        self.editor.textEdit.insert_text(["This is one line.", "This is the second.", "This is 3?"])
        self.assertEqual(self.editor.textEdit.toPlainText(), "This is one line.\nThis is the second.\nThis is 3?")

class testDialogWindow(QDialog, Ui_testDialog):
    """Dialog to run selected tests for editor and transcript.
    """
    def __init__(self, editor):
        super().__init__()
        self.setupUi(self)
        self.editor = editor
        self.runTest.clicked.connect(self.run_tests)
        self.selectAll.clicked.connect(self.select_all)
        self.unselectAll.clicked.connect(self.unselect_all)
        self.selection = {"step_ConfirmFiles": "Setup files are present", 
                    "step_Stroke": "Strokes create output and are logged", 
                    "step_AddRemoveDict": "Add and remove new dict",
                    "step_WriteTwoLine": "Write correctly with new line in translation",
                    "step_SplitPar": "Split paragraph and undo",
                    "step_SplitParSpace": "Split paragraph with space involved and undo",
                    "step_MergePar": "Merge paragraph, space involved, and undo",
                    "step_CheckStyleAttr": "Text properly styled when loaded",
                    "step_ChangeStyle": "Text properly styled when style changed manually",
                    "step_ColorHighlight": "Change highlight color",
                    "step_SwitchTranscriptsPage": "Change page param with transcript switch",
                    "step_insertText": "Inserting normal text"}
        last = len(self.selection)
        counter = 0
        for i, des in self.selection.items():
            item = QListWidgetItem()
            item.setText(des)
            item.setData(Qt.UserRole, i)
            item.setCheckState(Qt.Unchecked)
            counter += 1
            if counter == last:
                item.setCheckState(Qt.Checked)
            self.listSelection.addItem(item)
    def select_all(self):
        for index in range(0, self.listSelection.count()):
            item = self.listSelection.item(index)
            item.setCheckState(Qt.Checked)
    def unselect_all(self):
        for index in range(0, self.listSelection.count()):
            item = self.listSelection.item(index)
            item.setCheckState(Qt.Unchecked)        
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
        selection = []
        for index in range(0, self.listSelection.count()):
            item = self.listSelection.item(index)
            if item.checkState() == Qt.Checked:
                selection.append(item.data(Qt.UserRole))
        suite.addTest(TestTextEdit("testMonolithic", self.editor, selection))
        # suite.addTest(TestTextEdit("testConfirmFiles", self.editor))
        res = TextTestRunner(stream = res_output, verbosity=1).run(suite)
        self.output.clear()
        self.output.setPlainText(res_output.getvalue())
        return res
