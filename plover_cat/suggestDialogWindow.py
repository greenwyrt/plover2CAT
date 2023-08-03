from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from collections import Counter
from plover import log
from plover.steno import normalize_steno
from plover_cat.suggest_dialog_ui import Ui_suggestDialog
# from wiki
stopwords = ['a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', "aren't", 'as', 'at', 
            'be', 'because', 'been', 'between', 'both', 'but', 'by', "can't", 'cannot', 'could', "couldn't", 'did', "didn't", 
            'do', 'does', "doesn't", 'doing', "don't", 'down', 'for', 'from', 'further', 'had', "hadn't", 'has', "hasn't", 
            'have', "haven't", 'having', 'he', "he'd", "he'll", "he's", 'her', 'here', "he", 'him', 'himself', 'his', 'how', 
            "how's", "i", "i'd", "i'll", "i'm", "i've", 'if', 'in', 'into', 'is', "isn't", 'it', "it's", 'its', 'itself', 
            "let's", 'me', 'more', 'most', "mustn't", 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 
            'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', "shan't", 'she', "she'd", "she'll", 
            "she's", 'should', "shouldn't", 'so', 'some', 'such', 'than', 'that', "that's", 'the', 'their', 'theirs', 'them', 
            'themselves', 'then', 'there', "there's", 'these', 'they', "they'd", "they'll", "they're", "they've", 'this', 
            'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', "wasn't", 'we', "we'd", "we'll", "we're", 
            "we've", 'were', "weren't", 'what', "what's", 'when', "when's", 'where', "where's", 'which', 'while', 'who', "who's",
            'whom', 'why', "why's", 'with', "won't", 'would', "wouldn't", 'you', "you'd", "you'll", "you're", "you've", 'your',
            'yours', 'yourself', 'yourselves']

def extract_ngram(text, n = 2):
    return zip(*[text.split()[i:] for i in range(n)])

class suggestDialogWindow(QDialog, Ui_suggestDialog):
    # insert_autocomplete = pyqtSignal(tuple)
    def __init__(self, text, engine, scowl_dict):
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
        # one day, lookup strokes from rtf or other transcripts
        res = self.engine.reverse_lookup(translation)
        return(list(res))
    def update_text(self, text):
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
        selected_row = self.displaySuggest.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Add to dictionary", "No row selected.")
            return
        word = self.displaySuggest.item(selected_row, 0).text()
        stroke = self.displaySuggest.item(selected_row, 1).text()
        if len(stroke) == 0:
            QMessageBox.warning(self, "Add to dictionary", "Missing translation outline.")    
            return
        self.engine.add_translation(normalize_steno(stroke, strict = True), word.strip())