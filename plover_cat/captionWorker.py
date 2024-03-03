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
    def __init__(self, max_length = None, max_lines = None, remote = None, endpoint = None, port = None, password = None):
        """Generate captions based on user settings and endpoint parameters 
        for caption display and to send to endpoints. ``captionWorker`` is 
        put into another thread and doesn't run on the main event thread.
        Text gets ingested and then sent out as formatted caption lines.
        :param max_length: maximum number of characters for each caption line, 
            suggested value 32, default None
        :type max_length: int, optional
        :max_lines: maximum number of captions lines to display, 
            suggested value 3, default None
        :type max_lines: int, optional
        :param remote: name of remote endpoint, can only be one of supported, default None
        :type remote: string, optional
        :param endpoint: URL or local port depending on what kind of remote, may be authentication token,
            suggested localhost in the case of OBS, default None
        :type endpoint: string, optional
        :param port: port number to use with endpoint, suggested 4455 for OBS, default None
        :type port: string, optional
        :param password: password to use along with other fields above, default None
        :type password: string, optional
        """
        QObject.__init__(self)
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
        """Queue containing text split into word chunks."""
        self.cap_queue = deque(maxlen = max_lines)
        """Queue containing formatted caption lines ready for display."""
        self.next_word = "" 
        self.zoom_seq = 1
        """Line number for caption, required for Zoom captions."""
    def intake(self, text):
        """Receive text from main editor and create work chunks for captions
        :param text: text written into editor
        :type text: str, required
        """
        text_time = datetime.now()
        chunks = [i for i in wordsep_simple_re.split(text) if i]
        for i in chunks:
            # tuple, first text, then time
            self.word_queue.put((i, text_time))
        self.make_caps()
    def make_caps(self):
        """Ingest word chunks from queue and put lines into caption queue.
        """
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
        """Take caption from queue and send to display, and also if endpoint is defined.
        """
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
        """Clean up instance and emit signal for finish
        """
        self.finished.emit()
    def send_msteams(self, cap):
        """Take caption and send post to Microsoft Teams session
        """
        req = request.Request(self.endpoint, method = "POST")
        req.data = cap.encode()
        req.add_header('Content-Type', 'text/plain')
        req.add_header('Content-Length', len(cap)) 
        try:
            r = request.urlopen(req)
        except HTTPError as err:
            self.postMessage.emit(f"Captioning: send to Microsoft Teams failed with error code {err.code}.")
    def send_zoom(self, cap):
        """Take caption and send post to Zoom session
        """
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
        """Take caption and send to OBS using obsws_python
        """
        try:
            res = self.obs.send_stream_caption(cap)
        except OBSSDKRequestError as err:
            self.postMessage.emit(f"Captioning: send to OBS failed with error code {err.code}")
        except Exception as e:
            self.postMessage.emit(f"Captioning: send to OBS failed. Error message is {e}")
