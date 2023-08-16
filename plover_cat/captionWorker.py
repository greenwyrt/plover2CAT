from urllib import request, parse
from urllib.error import HTTPError
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from queue import Queue, Empty
from plover_cat.steno_objects import wordsep_simple_re
from datetime import datetime
import obsws_python as obs

class captionWorker(QObject):
    capSend = pyqtSignal(str)
    finished = pyqtSignal()
    postMessage = pyqtSignal(str)
    def __init__(self, max_length = None, word_delay = None, time_delay = 1000, remote = None, endpoint = None, port = None, password = None):
        QObject.__init__(self)
        self.word_delay = word_delay
        self.max_length = max_length
        self.remote = remote
        self.endpoint = endpoint
        self.port = port
        self.password = password
        if self.port:
            self.obs = obs.ReqClient(host='localhost', port=self.port, password=self.password, timeout=3) 
        self.word_queue = Queue()
        self.cap_queue = Queue()
        self.cap_timer = QTimer()
        self.cap_timer.start(time_delay)
        self.cap_timer.timeout.connect(self.send_cap)
        self.cap_line = ""
        self.next_word = "" 
        self.zoom_seq = 1
    def intake(self, text):
        text_time = datetime.now()
        chunks = [i for i in wordsep_simple_re.split(text) if i]
        for i in chunks:
            # tuple, first text, then time
            self.word_queue.put((i, text_time))
        self.make_caps()
    def make_caps(self):
        while not self.word_queue.empty():
            self.next_word, text_time = self.word_queue.get()
            if self.max_length != 0 and (len(self.cap_line) + len(self.next_word)) > self.max_length:
                self.cap_queue.put((self.cap_line, text_time))
                self.cap_line = self.next_word
                # self.send_cap()
            elif "\u2029" in self.next_word:
                self.cap_line += self.next_word.replace("\u2029", "")
                self.cap_queue.put((self.cap_line, text_time))
                self.cap_line = ""
                # self.send_cap()
            else:
                self.cap_line += self.next_word
    def send_cap(self):
        # print(f"queue size {self.cap_queue.qsize()}.")
        try:
            cap, time = self.cap_queue.get_nowait()
            self.capSend.emit(cap)
            if self.endpoint:
                if self.remote == "Microsoft Teams":
                    self.send_msteams(cap)
                elif self.remote == "Zoom":
                    self.send_zoom(cap)
            if self.remote == "OBS":
                self.send_obs(cap)
        except Empty:
            pass
    def clean_and_stop(self):
        self.cap_timer.stop()
        self.finished.emit()
    def send_msteams(self, cap):
        req = request.Request(self.endpoint, method = "POST")
        req.data = cap.encode()
        req.add_header('Content-Type', 'text/plain')
        req.add_header('Content-Length', len(cap)) 
        try:
            r = request.urlopen(req)
        except HTTPError as err:
            # print(err.code)
            self.postMessage.emit(f"Captioning: send to Microsoft Teams failed with error code {err.code}.")
    def send_zoom(self, cap):
        # req = request.Request(self.endpoint, method = "POST")
        req = request.Request(self.endpoint + f"&seq={self.zoom_seq}&lang=en-US", method = "POST")      
        self.zoom_seq += 1
        req.data = cap.encode()  
        req.add_header('Content-Type', 'text/plain')
        req.add_header('Content-Length', len(cap)) 
        try:
            r = request.urlopen(req)
        except HTTPError as err:
            # print(err.code)
            self.postMessage.emit(f"Captioning: send to Zoom failed with error code {err.code}.")  
    def send_obs(self, cap):
        print("obs")
        res = self.obs.send_stream_caption(cap)