import codecs
import struct
import re
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QProgressBar, QApplication
from copy import deepcopy
from datetime import datetime
from pyparsing import (
    Literal, 
    Word, 
    printables, 
    alphas, 
    nums, 
    hexnums,
    common,
    White,
    replace_with,
    Opt, 
    Or,
    one_of,
    Combine, 
    OneOrMore, 
    Group,
    Suppress,
    Forward,
    ParseResults
)

from plover import log

from plover_cat.steno_objects import *

# control chars \ { }


LBRACE, RBRACE, BKS = map(Suppress, "{}\\")


text_whitespace = Opt(White(" \t")) + Word(printables, exclude_chars="\\{}") + Opt(White(" \t"))
text_whitespace.set_name("text")
# text_whitespace.leave_whitespace()

# special chars that exist as control words, should be replaced by actual unicode equivalents, 
tab_char = Literal("\\tab").set_parse_action(replace_with("\N{CHARACTER TABULATION}")) # "\t" or "\N{CHARACTER TABULATION}"
emdash_char = Literal("\\emdash").set_parse_action(replace_with("\N{EM DASH}")) # "\u2014" or "\N{EM DASH}"
endash_char = Literal("\\endash").set_parse_action(replace_with("\N{EN DASH}")) # "\u2013" or "\N{EN DASH}"
emspace_char = Literal("\\emspace").set_parse_action(replace_with("\N{EM SPACE}")) # "\u2003" or "\N{EM SPACE}"
enspace_char = Literal("\\enspace").set_parse_action(replace_with("\N{EN SPACE}")) # "\u2002" or "\N{EN SPACE}"
nonbreaking_space = Literal("\\~").set_parse_action(replace_with("\N{NO-BREAK SPACE}")) # "\u00A0" or "\N{NO-BREAK SPACE}"
soft_hyphen = Literal("\\-").set_parse_action(replace_with("\N{SOFT HYPHEN}")) # "\u00AD" or "\N{SOFT HYPHEN}"
nonbreaking_hyphen = Literal("\\_").set_parse_action(replace_with("\N{HYPHEN}")) # "\u2010" or "\N{HYPHEN}"
bullet_char = Literal("\\bullet").set_parse_action(replace_with("\N{BULLET}"))
lquote_char = Literal("\\lquote").set_parse_action(replace_with("\N{LEFT SINGLE QUOTATION MARK}"))
rquote_char = Literal("\\rquote").set_parse_action(replace_with("\N{RIGHT SINGLE QUOTATION MARK}"))
ldblquote_char = Literal("\\ldblquote").set_parse_action(replace_with("\N{LEFT DOUBLE QUOTATION MARK}"))
rdblquote_char = Literal("\\rdblquote").set_parse_action(replace_with("\N{RIGHT DOUBLE QUOTATION MARK}"))
open_brace = Literal("\\{")
close_brace = Literal("\\}")

def pa(s, l, t):
    hex_val = [int(tokn, 16) for tokn in t]
    byte_val = struct.pack('B', int(hex_val[0]))
    return(byte_val.decode("cp437"))

hex_char = Group(Suppress(BKS + "'") + Word(hexnums).set_parse_action(pa).set_results_name("hex_char")) # hex in form \'xx
hex_char.set_name("Hexadecimal character")

def paste_text(s, l, t):
    command_dict = {}
    command_dict["control"] = "text"
    command_dict["value"] = "".join(t[0])
    return(command_dict)

text_and_chars = Group(OneOrMore(text_whitespace ^ tab_char ^ emdash_char ^ endash_char ^ 
    emspace_char ^ enspace_char ^ nonbreaking_space ^ soft_hyphen ^ 
    nonbreaking_hyphen ^ hex_char ^ open_brace ^ close_brace ^ bullet_char ^ 
    lquote_char ^ rquote_char ^ ldblquote_char ^ rdblquote_char))
text_and_chars.set_name("text")
text_and_chars.set_name("Plain text")
text_and_chars.set_parse_action(paste_text)

expr = Forward()

def control_parse(s, l, t):
    command_dict = {}
    command_dict["control"] = t[0]["control"]
    try:
        command_dict["value"] = t[0]["num"]
    except KeyError:
        pass
    try:
        t[0]["ending"]
        command_dict["ending"] = True
    except KeyError:
        pass
    return(command_dict)

control = Group(
    BKS + 
    Combine(
        Word(alphas)("control") + 
        Opt(Word(nums + '-').set_parse_action(common.convert_to_integer))("num") + 
        Opt(White(" ", max=1)) + 
        Opt(Literal(";"))("ending")
        )
    )
control.set_name("control")
control.set_parse_action(control_parse)

def control_parse_ignore(s, l, t):
    command_dict = t[0][1]
    command_dict["ignore"] = True
    return(command_dict)

ignore = Group(Literal("\\*")("ignore") + control)
ignore.set_name("ignore")
ignore.set_parse_action(control_parse_ignore)

expr <<= OneOrMore(ignore("ignore*") | hex_char("hex_char*") | control("control*") | text_and_chars("text*") | Group(LBRACE + expr + RBRACE)("group*"))
expr.set_name("RTF")

style_string = Suppress(Literal("\\par\\pard")) + OneOrMore(control("control*"))

def twip_to_in(twips):
    return(twips / 1440)

def in_to_twip(inches):
    if isinstance(inches, str):
        inches = float(inches.replace("in", ""))
    return(int(inches * 1440))

def append_value(dict_obj, key, value):
    # Check if key exist in dict or not
    if key in dict_obj:
        # Key exist in dict.
        # Check if type of value of key is list or not
        if not isinstance(dict_obj[key], list):
            # If type is not list then make it list
            dict_obj[key] = [dict_obj[key]]
        # Append the value in list
        dict_obj[key].append(value)
    else:
        # As key is not in dict,
        # so, add key-value pair
        dict_obj[key] = value

def collapse_dict(element):
    new_dict = {}
    for i in element:
        if "value" in i:
            append_value(new_dict, i["control"], i["value"])
        else:
            append_value(new_dict, i["control"], "")
    return(new_dict)

# with rtf_steno parsing, each control word parses as a dict, and text as a dict
# each group parses as a list (ParseResults), and so results in a list with control words as dicts, more groups as lists, and text as dicts
class rtf_steno:
    def __init__(self, file_name, progress_bar = None):
        self.rtf_file = file_name
        self.parse_results = None
        self.scanned_styles = {}
        self.framerate = 30
        self.fonts = {}
        self.styles = {}
        self.page = {}
        # mimic json_document format in this dict
        self.paragraphs = {}
        # list of strokes, within par, empty at next par and append to paragraphs 
        self.par = []
        self.par_style = ""
        self.date = ""
        # dict of timecodes to bump off
        self.timecode = { "milli": "000", "sec": "00", "min": "00", "hour": "00"}
        self.steno = ""
        self.text = ""
        self.start_parsing_text = False
        self.defaultfont = ""
        self.fonts = {}
        self.progress_bar = progress_bar
    def parse_framerate(self, element):
        element_dict = element[0]
        self.framerate = element_dict["value"]
    def parse_date(self, element):
        for i in element:
            try:
                control_word = i[0]["control"]
                if control_word == "creatim":
                    select_dict = i
                    break
            except:
                pass
        for i in select_dict:
            if i["control"] == "yr":
                year = i["value"]
            elif i["control"] == "mo":
                month = i["value"]
            elif i["control"] == "dy":
                day = i["value"]
        self.date = "%s-%s-%s" % (year, month, day)
    def parse_font(self, element):
        for i in element[1:len(element)]:
            new_font_dict = collapse_dict(i)
            self.fonts[str(new_font_dict["f"])] = new_font_dict
    def parse_styles(self, element):
        for i in element[1:len(element)]:
            new_style_dict = collapse_dict(i)
            # libreoffice replaces spaces with _20_ in style name
            split_style_name = new_style_dict["text"]
            correct_style_name = "_20_".join(split_style_name.split(" ")).replace(";", "")
            new_style_dict["text"] = correct_style_name
            self.styles[str(new_style_dict["s"])] = new_style_dict
    def parse_page(self, element):
        self.page[element["control"]] = round(twip_to_in(element["value"]), 2)
    def parse_timecode(self, element, split = ":"):
        time_element = element[1]["value"].split(split)
        # previous timecode is structured to take advantage of dict being in order
        # plover is python 3.7 and above so this should work properly
        split_codes = ["%02d" % int(i) for i in reversed(time_element)]
        # remember that last element in original timecode is frame, needs millisecond
        split_codes[0] = "%03d" % self.convert_framerate_milli(int(split_codes[0]))
        for key_index, text in enumerate(split_codes):
            self.timecode[list(self.timecode)[key_index]] = text
    def parse_par_style(self, element):
        style_index = str(element["value"])
        style_name = self.styles[style_index]["text"]
        self.par_style = style_name
    def parse_cxa(self, element):
        cxa_dict = collapse_dict(element)
        self.steno = ""
        self.text = cxa_dict["text"]
        timestamp = "%sT%s:%s:%s.%s" % (self.date, self.timecode["hour"], self.timecode["min"], self.timecode["sec"], self.timecode["milli"])
        ael = automatic_text(prefix = cxa_dict["text"], time = timestamp)
        self.par.append(ael.to_json())
    def parse_steno(self, element):
        try:
            stroke = element[1]["value"]
        except:
            stroke = ""
        self.steno = stroke
    def parse_text(self, element):
        self.text = element["value"]
    def append_stroke(self):
        timestamp = "%sT%s:%s:%s.%s" % (self.date, self.timecode["hour"], self.timecode["min"], self.timecode["sec"], self.timecode["milli"])
        ael = stroke_text(time = timestamp, stroke = self.steno, text = self.text)
        self.par.append(ael.to_json())
    def convert_framerate_milli(self, frames):
        milli = 1000 * frames / self.framerate
        return(milli)
    def set_new_paragraph(self):
        par_num = str(len(self.paragraphs))
        # par_text = "".join([stroke[2] for stroke in self.par])
        # this last stroke should capture the stroke emitting \par
        timestamp = "%sT%s:%s:%s.%s" % (self.date, self.timecode["hour"], self.timecode["min"], self.timecode["sec"], self.timecode["milli"])
        last_stroke = stroke_text(time = timestamp, stroke = self.steno, text = "\n")
        self.par.append(last_stroke.to_json())
        strokes = self.par
        par_dict = {}
        par_dict["strokes"] = strokes
        par_dict["creationtime"] = strokes[0]["time"]
        par_dict["style"] = self.par_style
        self.paragraphs[par_num] = par_dict
        self.par = []
    def parse_document(self):
        parse_results = expr.parse_file(self.rtf_file)
        if self.progress_bar:
            self.progress_bar.setMaximum(len(parse_results[0]))
        self.parse_results = parse_results
        for num, i in enumerate(parse_results[0]):
            if isinstance(i, dict):
                command_name = i["control"]
                if command_name in ["paperh", "paperw", "margt", "margb", "margl", "margr"]:
                    self.parse_page(i)
                if command_name == "deffont":
                    self.defaultfont = i["value"] # this is a number representing index into fonts
                if command_name == "par":
                    if not self.start_parsing_text:
                        self.start_parsing_text = True
                    else:
                        self.set_new_paragraph()
                if command_name == "s":
                    self.parse_par_style(i)
                if command_name == "text" and self.start_parsing_text:
                    self.parse_text(i)
                    self.append_stroke()
            elif isinstance(i, ParseResults):
                command_name = i[0]["control"]
                if command_name == "stylesheet":
                    self.parse_styles(i)
                if command_name == "fonttbl":
                    self.parse_font(i)
                if command_name == "info":
                    self.parse_date(i)
                if command_name == "cxframes":
                    self.parse_framerate(i)
                if command_name == "cxt":
                    self.parse_timecode(i)
                if command_name == "cxs":
                    self.parse_steno(i)
                if command_name == "cxa":
                    self.parse_cxa(i)
            else:
                pass
            if self.progress_bar:
                self.progress_bar.setValue(num)
                QApplication.processEvents()
        self.set_new_paragraph()
        self.scan_par_styles()
    def scan_par_styles(self):
        with open(self.rtf_file, 'r') as f:
            data = f.read().rstrip()
        style_list = []
        for i in style_string.scanString(data):
            style_list.append(i[0].asList())
        # print(len(style_list))
        par_style_index = 0
        for ind, el in enumerate(style_list):
            new_style_dict = collapse_dict(el)
            # print(new_style_dict)
            if "s" in new_style_dict:
                self.scanned_styles[str(par_style_index)] = new_style_dict
                par_style_index += 1
                
# test_string = """
# {\\rtf1\\ansi\\deff1
# {\\fonttbl
# {\\f0\\fcharset1 Times New Roman;}
# {\\f1\\froman\\fcharset1 Times New Roman{\\*\\falt Base Font};}}
# {\\colortbl;\\red0\\green0\\blue0;\\red0\\green0\\blue255;\\red0\\green255\\blue255;\\red0\\green255\\blue0;}
# {\\xe{\\*\cxexnum 1}Exhibit 1:  A knife }} sss
# """
# test_string = r"{\par\pard\s0\f0\fs24{\*\cxt 20:46:25:00}{\*\cxs WELG}Welcome{\*\cxt 20:46:26:00}{\*\cxs TOT} to the{\*\cxt 20:46:27:00}{\*\cxs SROEUS} Voice{\*\cxt 20:46:27:00}{\*\cxs -F} of{\*\cxt 20:46:27:00}{\*\cxs PHERBG} America{\xe{\*\cxexnum 1}Exhibit 1:  A knife }{\*\cxt 20:46:28:00}{\*\cxs AES}'s{\*\cxt 20:46:29:00}{\*\cxs TPHUS} News{\*\cxt 20:46:30:00}{\*\cxs WORDZ} Words{\*\cxt 20:46:30:00}{\*\cxs TP-PL}.}"


# res = expr.parse_string(test_string)
# test_rtf = rtf_steno("plover_cat/test.rtf")
# test_rtf.parse_document()
# test_rtf.scan_par_styles()
# test_rtf.parse_results[0][9]

def rtf_to_qfont(font):
    font_dict = {}
    if "text" in font:
        qt_font = QFont(text)
    else:
        qt_font = QFont()
    if "froman" in font:
        qt_font.setStyleHint(QFont.Times)
    if "fswiss" in font:
        qt_font.setStyleHint(QFont.SansSerif)
    if "fmodern" in font:
        qt_font.setStyleHint(QFont.Courier)
    if "fscript" in font:
        qt_font.setStyleHint(QFont.Cursive)
    if "fdecor" in font:
        qt_font.setStyleHint(QFont.Decorative)
    return(qt_font)

def modify_styleindex_to_name(styles, style_names):
    for key, i in styles.items():
        if "parentstylename" in i:
            style_names[i["parentstylename"]]
            i["parentstylename"] = style_names[i["parentstylename"]]
        if "nextstylename" in i:
            i["nextstylename"] = style_names[int(i["nextstylename"])]
        styles[key] = i
    return(styles)

def extract_par_style(style_dict):
    one_style_dict = {}
    one_part_dict = {}
    one_text_dict = {}
    if "s" in style_dict:
        one_style_dict["styleindex"] = str(style_dict["s"])
    if "sbasedon" in style_dict:
        one_style_dict["parentstylename"] = style_dict["sbasedon"]
    if "snext" in style_dict:
        one_style_dict["nextstylename"] = style_dict["snext"]
    if "li" in style_dict:
        one_part_dict["marginleft"] = "%.2fin" % twip_to_in(style_dict["li"])
    if "ri" in style_dict:
        one_part_dict["marginright"] = "%.2fin" % twip_to_in(style_dict["ri"])
    if "fi" in style_dict:
        one_part_dict["textindent"] = "%.2fin" % twip_to_in(style_dict["fi"])
    if "ql" in style_dict:
        one_part_dict["textalign"] = "left"
    if "qr" in style_dict:
        one_part_dict["textalign"] = "right"
    if "qj" in style_dict:
        one_part_dict["textalign"] = "justify"
    if "qc" in style_dict:
        one_part_dict["textalign"] = "center"
    if "sb" in style_dict:
        one_part_dict["margintop"] = "%.2fin" % twip_to_in(style_dict["sb"])
    if "sa" in style_dict:
        one_part_dict["marginbottom"] = "%.2fin" % twip_to_in(style_dict["sa"])
    if "tx" in style_dict:
        if isinstance(style_dict["tx"], list):
            tab_pos = ["%.2fin" % twip_to_in(i) for i in style_dict["tx"]]
        else:
            tab_pos = ["%.2fin" % twip_to_in(style_dict["tx"])]
        one_part_dict["tabstop"] = tab_pos
    if "f" in style_dict:
        one_text_dict["fontindex"] = style_dict["f"]
    if "fs" in style_dict:
        one_text_dict["fontsize"] = str(style_dict["fs"]/2)
    if "i" in style_dict:
        one_text_dict["fontstyle"] = "italic"
    if "b" in style_dict:
        one_text_dict["fontweight"] = "bold"
    if "ul" in style_dict:
        one_text_dict["textunderlinetype"] = "single"
        one_text_dict["textunderlinestyle"] = "solid"
    one_style_dict["paragraphproperties"] = one_part_dict
    one_style_dict["textproperties"] = one_text_dict
    return(one_style_dict)

def load_rtf_styles(parse_results):
    log.debug(f"Loading RTF styles from {parse_results.rtf_file}")
    style_dict = {}
    for k, v in parse_results.styles.items():
        style_name = v["text"]
        style_num = 0
        while style_name in list(style_dict.keys()):
            style_num += 1
            style_name = re.sub("\\d+$", "", style_name) + str(style_num)
        style_dict[style_name] = extract_par_style(v)
    styles = []
    for k, v in style_dict.items():
        styles.append(k)
    style_dict = modify_styleindex_to_name(style_dict, styles)
    font_names = []
    for i, font in parse_results.fonts.items():
        font_names.append(font["text"])
    indiv_style = {}
    for key, par_style in parse_results.scanned_styles.items():
        par_dict = extract_par_style(par_style)
        # indiv_style[key] = extract_par_style(par_style)
        if "textproperties" in par_dict and "fontindex" in par_dict["textproperties"]:
            fontindex = str(par_dict["textproperties"]["fontindex"])
            font_dict = parse_results.fonts[fontindex]
            if "text" in font_dict:
                par_dict["textproperties"]["fontname"] = font_dict["text"].replace(";", "")
                par_dict["textproperties"]["fontfamily"] = font_dict["text"].replace(";", "")
            if "froman" in font_dict:
                par_dict["textproperties"]["fontfamilygeneric"] = "roman"
            if "fswiss" in font_dict:
                par_dict["textproperties"]["fontfamilygeneric"] = "swiss"
            if "fmodern" in font_dict:
                par_dict["textproperties"]["fontfamilygeneric"] = "modern"
            if "fscript" in font_dict:
                par_dict["textproperties"]["fontfamilygeneric"] = "script"
            if "fdecor" in font_dict:
                par_dict["textproperties"]["fontfamilygeneric"] = "decorative"
        indiv_style[key] = par_dict
    renamed_indiv_style = []
    for index, style in indiv_style.items():
        par_style = style
        doc_style = deepcopy(list(style_dict.values())[int(style["styleindex"])])
        doc_style.update(par_style)
        found_style = False
        for k, v in style_dict.items():
            if doc_style == v:
                renamed_indiv_style.append(k)
                found_style = True
                break
        if found_style:
            continue
        style_parent_name = list(style_dict.keys())[int(style["styleindex"])]
        detect_int = re.search("\\d+$", style_parent_name)
        if detect_int:
            style_num = int(detect_int.group()) + 1
        else:
            style_num = 0
        new_style_name = re.sub("\\d+$", "", style_parent_name) + str(style_num)
        while new_style_name in list(style_dict.keys()):
            style_num += 1
            new_style_name = re.sub("\\d+$", "",style_parent_name) + str(style_num)
        style_dict[new_style_name] = doc_style
        renamed_indiv_style.append(new_style_name)
    return(style_dict, renamed_indiv_style)    

def import_version_one(json_document):
    """Formats JSON file with older transcript format into standard transcript dict form"""
    transcript_dict = {}
    for key, value in json_document.items():
        if not key.isdigit():
            continue
        el_list = []
        for el in value["data"]["strokes"]:
            el_dict = {"time": el[0], "stroke": el[1], "data": el[2]}
            if len(el) == 4:
                el_dict["audiotime"] = el[4]
            new_stroke = stroke_text()
            new_stroke.from_dict(el_dict)
            el_list.append(new_stroke)
        block_data = {}
        for k, v in value["data"].items():
            block_data[k] = v
        block_data["strokes"] = element_collection(el_list).to_json()
        transcript_dict[str(key)] = block_data
    return(transcript_dict)

def import_version_two(json_document):
    """Formats JSON file with newer transcript format into standard transcript dict form"""
    return(json_document)