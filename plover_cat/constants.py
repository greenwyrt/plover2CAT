import re
re_strokes = re.compile(r"\s\s>{1,5}(.*)$") #: Find strokes in Tapey Tape file
steno_untrans = re.compile(r"(?=[STKPWHRAO*EUFBLGDZ])S?T?K?P?W?H?R?A?O?\*?E?U?F?R?P?B?L?G?T?S?D?Z?")
clippy_strokes = re.compile(r'\x1B\[38;2;104;157;106m(?!<)(.*?)\x1B\[0m') #: Find strokes in Plover Clippy file

default_styles = {
    "Normal": {
        "family": "paragraph",
        "nextstylename": "Normal",
        "textproperties": {
            "fontfamily": "Courier New",
            "fontname": "'Courier New'",
            "fontsize": "12pt"
        },
        "paragraphproperties": {
            "linespacing": "200%"
        }
    },
    "Question": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Answer",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Answer": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Question",
        "paragraphproperties": {
            "textindent": "0.5in",
            "tabstop": "1in"
        }
    },
    "Colloquy": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",  
        "paragraphproperties": {
            "textindent": "1.5in"
        }     
    },
    "Quote": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal", 
        "paragraphproperties": {
            "marginleft": "1in",
            "textindent": "0.5in"
        } 
    },
    "Parenthetical": {
        "family": "paragraph",
        "parentstylename": "Normal",
        "nextstylename": "Normal",
        "paragraphproperties": {
            "marginleft": "1.5in"
        }        
    }
}

default_config = {
    "base_directory": "",
    "style": "styles/default.json",
    "dictionaries": [],
    "page_width": "8.5",
    "page_height": "11",
    "page_left_margin": "1.75",
    "page_top_margin": "0.7874",
    "page_right_margin": "0.3799",
    "page_bottom_margin": "0.7874",
    "page_line_numbering": False
}
# shortcuts based on windows media player
default_dict = {
    "S-FRLG":"{#control(s)}", # save
    "P-FRLG":"{#control(p)}", # play/pause
    "W-FRLG":"{#control(w)}", # audio stop
    "HR-FRLG":"{#control(l)}", # skip back
    "SKWR-FRLG":"{#control(j)}", # skip forward
    "KR-FRLG":"{#control(c)}", # copy
    "SR-FRLG":"{#control(v)}", # paste
    "KP-FRLG":"{#control(x)}", # cut
    "TP-FRLG":"{#control(f)}", # find
    "TKPW-FRLGS":"{#control(shift(g))}", # speed up
    "S-FRLGS":"{#control(shift(s))}", # slow down
    "STKPW-FRLG":"{#controls(z)}", # undo
    "KWR-FRLG":"{#controls(y)}", # redo
    "R-FRLGS":"{#control(shift(r))}" # define last
    # "-FRLG":"{#controls()}", FRLGS for ctrol + shift
    # "-PSZ":"{#control()}" alternative template with PSZ, FPSZ for control + shift
}

qt_key_nums = {
    48: 0,
    49: 1,
    50: 2,
    51: 3,
    52: 4,
    53: 5,
    54: 6,
    55: 7,
    56: 8,
    57: 9
}

# copied from plover-speaker-id
user_field_dict = {
  "SPEAKER_STPHAO": "Mr. Stphao",
  "SPEAKER_SKWRAO": "Ms. Skwrao",
  "SPEAKER_EUFPLT": "Mr. Eufplt",
  "SPEAKER_EURBGS": "Ms. Eurbgs",
}

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