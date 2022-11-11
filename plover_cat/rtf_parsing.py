import codecs
import struct

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

# control chars \ { }


LBRACE, RBRACE, BKS = map(Suppress, "{}\\")


text_whitespace = Word(printables, exclude_chars="\\{}") + Opt(White(" ", max=1))
text_whitespace.set_name("text")

# special chars that exist as control words, should be replaced by actual unicode equivalents, 
tab_char = Literal("\\tab").set_parse_action(replace_with("\N{CHARACTER TABULATION}")) # "\t" or "\N{CHARACTER TABULATION}"
emdash_char = Literal("\emdash").set_parse_action(replace_with("\N{EM DASH}")) # "\u2014" or "\N{EM DASH}"
endash_char = Literal("\endash").set_parse_action(replace_with("\N{EN DASH}")) # "\u2013" or "\N{EN DASH}"
emspace_char = Literal("\emspace").set_parse_action(replace_with("\N{EM SPACE}")) # "\u2003" or "\N{EM SPACE}"
enspace_char = Literal("\enspace").set_parse_action(replace_with("\N{EN SPACE}")) # "\u2002" or "\N{EN SPACE}"
nonbreaking_space = Literal("\~").set_parse_action(replace_with("\N{NO-BREAK SPACE}")) # "\u00A0" or "\N{NO-BREAK SPACE}"
soft_hyphen = Literal("\-").set_parse_action(replace_with("\N{SOFT HYPHEN}")) # "\u00AD" or "\N{SOFT HYPHEN}"
nonbreaking_hyphen = Literal("\_").set_parse_action(replace_with("\N{HYPHEN}")) # "\u2010" or "\N{HYPHEN}"
bullet_char = Literal("\\bullet").set_parse_action(replace_with("\N{BULLET}"))
lquote_char = Literal("\lquote").set_parse_action(replace_with("\N{LEFT SINGLE QUOTATION MARK}"))
rquote_char = Literal("\\rquote").set_parse_action(replace_with("\N{RIGHT SINGLE QUOTATION MARK}"))
ldblquote_char = Literal("\ldblquote").set_parse_action(replace_with("\N{LEFT DOUBLE QUOTATION MARK}"))
rdblquote_char = Literal("\\rdblquote").set_parse_action(replace_with("\N{RIGHT DOUBLE QUOTATION MARK}"))
open_brace = Literal("\{")
close_brace = Literal("\}")

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

control = Group(BKS + Combine(Word(alphas)("control") + Opt(Word(nums + '-').set_parse_action(common.convert_to_integer))("num") + Opt(Literal(";"))("ending")))
control.set_name("control")
control.set_parse_action(control_parse)

def control_parse_ignore(s, l, t):
    command_dict = t[0][1]
    command_dict["ignore"] = True
    return(command_dict)

ignore = Group(Literal("\*")("ignore") + control)
ignore.set_name("ignore")
ignore.set_parse_action(control_parse_ignore)

expr <<= OneOrMore(ignore("ignore*") | hex_char("hex_char*") | control("control*") | text_and_chars("text*") | Group(LBRACE + expr + RBRACE)("group*"))
expr.set_name("RTF")

def twip_to_in(twips):
    return(twips / 1440)

def collapse_dict(element):
    new_dict = {}
    for i in element:
        try:
            new_dict[i["control"]] = i["value"]
        except:
            pass
    return(new_dict)

class steno_rtf:
    def __init__(self, file_name):
        self.rtf_file = file_name
        self.parse_results = None
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
        self.timecode = { "milli": "", "sec": "", "min": "", "hour": ""}
        self.steno = ""
        self.text = ""
        self.start_parsing_text = False
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
    def parse_font(self):
        pass
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
    def parse_steno(self, element):
        try:
            stroke = element[1]["value"]
        except:
            stroke = ""
        self.steno = stroke
        # self.steno = stroke_element
    def parse_text(self, element):
        self.text = element["value"]
    def append_stroke(self):
        timestamp = "%sT%s:%s:%s.%s" % (self.date, self.timecode["hour"], self.timecode["min"], self.timecode["sec"], self.timecode["milli"])
        stroke = [timestamp, self.steno, self.text]
        self.par.append(stroke)
    def convert_framerate_milli(self, frames):
        milli = 1000 * frames / self.framerate
        return(milli)
    def set_new_paragraph(self):
        strokes = self.par
        par_num = str(len(self.paragraphs))
        par_text = "".join([stroke[2] for stroke in self.par])
        # this last stroke should capture the stroke emitting \par
        timestamp = "%sT%s:%s:%s.%s" % (self.date, self.timecode["hour"], self.timecode["min"], self.timecode["sec"], self.timecode["milli"])
        last_stroke = [timestamp, self.steno, "\n"]
        self.par.append(last_stroke)
        par_dict = {}
        par_dict["text"] = par_text
        par_dict["data"] = {"strokes": strokes, "creationtime": strokes[0][0]}
        par_dict["style"] = self.par_style
        self.paragraphs[par_num] = par_dict
        self.par = []
    def parse_document(self):
        parse_results = expr.parse_file(self.rtf_file)
        self.parse_results = parse_results
        for i in parse_results[0]:
            if isinstance(i, dict):
                command_name = i["control"]
                if command_name in ["paperh", "paperw", "margt", "margb", "margl", "margr"]:
                    self.parse_page(i)
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
                if command_name == "info":
                    self.parse_date(i)
                elif command_name == "cxframes":
                    self.parse_framerate(i)
                if command_name == "cxt":
                    self.parse_timecode(i)
                if command_name == "cxs":
                    self.parse_steno(i)
            else:
                pass
        self.set_new_paragraph()

