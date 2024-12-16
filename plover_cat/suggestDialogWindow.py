from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from collections import Counter
from plover import log
from plover.steno import normalize_steno
from plover_cat.helpers import extract_ngram
from plover_cat.constants import stopwords
from plover_cat.suggest_dialog_ui import Ui_suggestDialog

class suggestDialogWindow(QDialog, Ui_suggestDialog):
    """Analyze existing transcript for common phrases and words.

    The suggest dialog presently works by analyzing the open transcript,
    through other sources are possible in the future. It can do a word frequency
    search, an n-gram search, or both, filtering by minimum occurrence. The
    word frequency search can use the SCOWL size filter, 
    while very common words are filtered out first.
    
    :param text: string of text
    :type text: str
    :param engine: existing Plover engine
    :param scowl_dict: SCOWL word list packaged with Plover
    :type scowl_dict: dict
    """
    # insert_autocomplete = pyqtSignal(tuple)
    def __init__(self, text, engine, scowl_dict):
        """Sets up connections for analysis with dialog UI"""
        super().__init__()
        self.setupUi(self)  
        self.document = text
        self.engine = engine
        self.detect.clicked.connect(self.analyze)
        self.scowl_dict = scowl_dict
        # self.toAutocomplete.clicked.connect(self.send_autocomplete)
        self.toDictionary.clicked.connect(self.send_dictionary)
        self.displaySuggest.setColumnCount(3)
        self.displaySuggest.setHorizontalHeaderLabels(["Candidate", "Outline", "Alternative outlines"])
    def analyze(self):
        """Starts analyzing text based on selected filters and parameters."""
        search_type = self.searchType.currentText()
        if search_type == "Words only":
            result_list = self.analyze_words(self.scowlSize.currentText(), self.minOccur.value())
        elif search_type == "N-grams only":
            result_list = self.analyze_ngrams(self.minNgram.value(), self.maxNgram.value(), self.minOccur.value())
        else:
            n_list = self.analyze_ngrams(self.minNgram.value(), self.maxNgram.value(), self.minOccur.value())
            word_list = self.analyze_words(self.scowlSize.currentText(), self.minOccur.value())
            result_list = n_list + word_list
        self.displaySuggest.clear()
        self.displaySuggest.setRowCount(0)
        self.displaySuggest.setColumnCount(3)
        self.displaySuggest.setHorizontalHeaderLabels(["Candidate", "Outline", "Alternative outlines"])
        self.displaySuggest.setRowCount(len(result_list))
        for row, word in enumerate(result_list):
            self.displaySuggest.setItem(row, 0, QTableWidgetItem(word))
            outlines = self.get_outline(word)
            if outlines:
                self.displaySuggest.setItem(row, 1, QTableWidgetItem(outlines[0][0]))
                if len(outlines) > 1:
                    alternatives = ", ".join([out[0] for out in outlines])
                    self.displaySuggest.setItem(row, 2, QTableWidgetItem(alternatives))
            else:
                self.displaySuggest.setItem(row, 1, QTableWidgetItem(""))
                self.displaySuggest.setItem(row, 2, QTableWidgetItem(""))
    def analyze_ngrams(self, min_ngram = 2, max_ngram = 3, min_occurrence = 3):
        """Run n-gram search and filter for display."""
        log.debug("Running ngram search.")
        if max_ngram < min_ngram:
            max_ngram = min_ngram + 1
        word_counter = Counter()
        for n in range(min_ngram, max_ngram + 1):
            for par in self.document.splitlines():
                # print([" ".join(i) for i in list(extract_ngram(par, n))])
                word_counter.update(list(extract_ngram(par, n)))
        result_list = [" ".join(list(k)) for k, v in word_counter.items() if v >= min_occurrence]
        return(result_list)
    def analyze_words(self, scowl_size = 35,  min_occurrence = 1):
        """Run word search and filter based on occurrence and SCOWL size."""
        log.debug("Running word frequency search.")
        word_counter = Counter(self.document.split())
        common = result_list = [k for k, v in word_counter.items() if v >= min_occurrence]
        result_list = []
        if scowl_size == "":
            for ind, word in enumerate(common):
                if word.lower() not in stopwords:
                    result_list.append(word)                    
        else:
            scowl_size = int(scowl_size)
            for ind, word in enumerate(common):
                if word in self.scowl_dict and self.scowl_dict[word] > scowl_size:
                    result_list.append(word)
                elif word not in self.scowl_dict:
                    result_list.append(word)
        return(result_list)
    def get_outline(self, translation):
        """Get list of outlines for translation from engine."""
        # one day, lookup strokes from rtf or other transcripts
        res = self.engine.reverse_lookup(translation)
        return(list(res))
    def update_text(self, text):
        """Update text for analysis"""
        self.document = text
    # def send_autocomplete(self):
    #     selected_row = self.displaySuggest.currentRow()
    #     if selected_row == -1:
    #         QMessageBox.warning(self, "Add to autocomplete", "No row selected.")
    #         return
    #     word = self.displaySuggest.item(selected_row, 0).text()
    #     stroke = self.displaySuggest.item(selected_row, 1).text()
    #     self.insert_autocomplete.emit((word, stroke))
    def send_dictionary(self):
        """Add selected outline to dictionary."""
        selected_row = self.displaySuggest.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Plover2CAT", "No row selected for adding to dictionary.")
            return
        word = self.displaySuggest.item(selected_row, 0).text()
        stroke = self.displaySuggest.item(selected_row, 1).text()
        if len(stroke) == 0:
            QMessageBox.warning(self, "Plover2CAT", "Missing translation outline to add to dictionary.")    
            return
        self.engine.add_translation(normalize_steno(stroke, strict = True), word.strip())