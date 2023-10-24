from urllib import request, parse
from urllib.error import HTTPError
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from queue import Queue, Empty
from collections import deque
from plover_cat.steno_objects import wordsep_simple_re
from datetime import datetime
import obsws_python as obs
from obsws_python.error import OBSSDKRequestError

class captionWorker(QObject):
    capSend = pyqtSignal(str)
    finished = pyqtSignal()
    postMessage = pyqtSignal(str)
    def __init__(self, max_length = None, max_lines = None, word_delay = None, remote = None, endpoint = None, port = None, password = None):
        QObject.__init__(self)
        self.word_delay = word_delay
        self.max_length = max_length
        self.max_lines = max_lines
        self.remote = remote
        self.endpoint = endpoint
        self.port = port
        self.password = password
        if self.remote == "OBS":
            if not self.port:
                self.port = "4455"
            if not self.endpoint:
                self.endpoint = "localhost"
            self.obs = obs.ReqClient(host=self.endpoint, port=self.port, password=self.password, timeout=3) 
            self.obs_queue = deque(maxlen = self.max_lines)
        self.word_queue = Queue()
        self.cap_queue = deque(maxlen = max_lines)
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
            try:
                last_cap, cap_time = self.cap_queue.pop()
            except IndexError:
                last_cap = ""
            if len(last_cap) + len(self.next_word) > self.max_length:
                self.cap_queue.append((last_cap, cap_time))
                self.cap_queue.append((self.next_word, text_time))
            elif "\u2029" in self.next_word:
                self.cap_queue.append((last_cap, cap_time))
                self.cap_queue.append((self.next_word.replace("\u2029", ""), text_time))
            else:
                self.cap_queue.append((last_cap + self.next_word, text_time))
            self.send_cap()
    def send_cap(self):
        try:
            last_caps = list(self.cap_queue)
            cap = "\n".join(c[0].lstrip(" ") for c in last_caps if c[0].lstrip(" "))
            self.capSend.emit(cap)
            if self.endpoint:
                if self.remote == "Microsoft Teams":
                    self.send_msteams(cap)
                elif self.remote == "Zoom":
                    self.send_zoom(cap)
                elif self.remote == "OBS":
                    self.send_obs(cap)
        except Empty:
            pass
    def clean_and_stop(self):
        self.finished.emit()
    def send_msteams(self, cap):
        req = request.Request(self.endpoint, method = "POST")
        req.data = cap.encode()
        req.add_header('Content-Type', 'text/plain')
        req.add_header('Content-Length', len(cap)) 
        try:
            r = request.urlopen(req)
        except HTTPError as err:
            self.postMessage.emit(f"Captioning: send to Microsoft Teams failed with error code {err.code}.")
    def send_zoom(self, cap):
        req = request.Request(self.endpoint + f"&seq={self.zoom_seq}&lang=en-US", method = "POST")      
        self.zoom_seq += 1
        req.data = cap.encode()  
        req.add_header('Content-Type', 'text/plain')
        req.add_header('Content-Length', len(cap)) 
        try:
            r = request.urlopen(req)
        except HTTPError as err:
            self.postMessage.emit(f"Captioning: send to Zoom failed with error code {err.code}.")  
    def send_obs(self, cap):
        try:
            res = self.obs.send_stream_caption(cap)
        except OBSSDKRequestError as err:
            self.postMessage.emit(f"Captioning: send to OBS failed with error code {err.code}")
        except Exception as e:
            self.postMessage.emit(f"Captioning: send to OBS failed. Error message is {e}")
