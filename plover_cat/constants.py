import re
re_strokes = re.compile(r"\s\s>{1,5}(.*)$")
steno_untrans = re.compile(r"(?=[STKPWHRAO*EUFBLGDZ])S?T?K?P?W?H?R?A?O?\*?E?U?F?R?P?B?L?G?T?S?D?Z?")
clippy_strokes = re.compile(r'\x1B\[38;2;104;157;106m(?!<)(.*?)\x1B\[0m')

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