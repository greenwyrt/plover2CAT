import pathlib
import json
import os
import time
import bisect
import textwrap
import re
from PyQt5.QtGui import QTextBlockFormat, QFont, QTextCharFormat, QTextOption
from PyQt5.QtCore import Qt
from plover.config import Config, DictionaryConfig
from plover import log
from dulwich.porcelain import open_repo_closing
from copy import deepcopy

from odf.style import (Style, TextProperties, ParagraphProperties, FontFace, PageLayout, 
PageLayoutProperties, MasterPage, TabStops, TabStop, GraphicProperties, Header, Footer)

def return_commits(repo, max_entries = 100):
    with open_repo_closing(repo) as r:
        walker = r.get_walker(max_entries = max_entries, paths=None, reverse=False)
        commit_strs = []
        for entry in walker:
            time_tuple = time.gmtime(entry.commit.author_time + entry.commit.author_timezone)
            time_str = time.strftime("%a %b %d %Y %H:%M:%S", time_tuple)
            commit_info = (entry.commit.id, time_str)
            commit_strs.append(commit_info)
    return(commit_strs)

def ms_to_hours(millis):
    """Converts milliseconds to formatted hour:min:sec.milli"""
    seconds, milliseconds = divmod(millis, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return ("%02d:%02d:%02d.%03d" % (hours, minutes, seconds, milliseconds))

def in_to_pt(inch):
    inch = float(inch)
    return(inch * 72)

def pixel_to_in(pixel):
    pixel = float(pixel)
    return(pixel / 96)

def in_to_pixel(inch):
    inch = float(inch)
    return(inch * 96)

def inch_to_spaces(inch, chars_per_in = 10):
    if isinstance(inch, str):
        inch = float(inch.replace("in", ""))
    return round((inch * chars_per_in))

def save_json(json_dict, file_path):
    """Save dict to json file"""
    file_path = pathlib.Path(file_path)
    if not file_path.parent.exists():
        file_path.parent.mkdir()
    with open(file_path, "w") as f:
        json.dump(json_dict, f, indent = 4)
        log.info("Data saved in " + str(file_path))

def add_custom_dicts(custom_dict_paths, dictionaries):
    """Takes list of dictionary paths, returns Plover dict config"""
    dictionaries = dictionaries[:]
    custom_dicts = [DictionaryConfig(path, True) for path in custom_dict_paths]
    return custom_dicts + dictionaries
## copied from plover_dict_commands
def load_dictionary_stack_from_backup(path):
    """Restore Plover dicts from backup file."""
    try:
        with open(path, 'r') as f:
            try:
                dictionaries = json.load(f)
            except json.JSONDecodeError:
                dictionaries = None
        if dictionaries:
            old_dictionaries = [DictionaryConfig.from_dict(x) for x in dictionaries]
            os.remove(path) #backup recovered, delete file
            return old_dictionaries
        else:
            return None
    except IOError:
        return None

def backup_dictionary_stack(dictionaries, path):
    """Takes Plover dict config, creates backup file."""
    log.info("Backing up Plover dictionaries to %s", path)
    if dictionaries:
        with open(path, 'w') as f:
            json.dump([DictionaryConfig.to_dict(d) for d in dictionaries], f)
    else:
        try:
            os.remove(path)
        except OSError:
            pass

def remove_empty_from_dict(d):
    if type(d) is dict:
        return dict((k, remove_empty_from_dict(v)) for k, v in d.items() if v and remove_empty_from_dict(v))
    elif type(d) is list:
        return [remove_empty_from_dict(v) for v in d if v and remove_empty_from_dict(v)]
    else:
        return d

def format_odf_text(block, style, chars_in_inch, page_width, line_num = 0):
    # block is QTextBlock
    # max_char fed into function is converted from page width or user setting (line num digits and timestamp digits are "outside of page")
    text = block.text()
    l_marg = 0
    r_marg = 0
    first_indent = 0
    block_data = block.userData().return_all()
    spaces_to_insert = 0
    if "paragraphproperties" in style:
        if "marginleft" in style["paragraphproperties"]:
            l_marg = inch_to_spaces(style["paragraphproperties"]["marginleft"], chars_in_inch)
        if "marginright" in style["paragraphproperties"]:
            r_marg = inch_to_spaces(style["paragraphproperties"]["marginright"], chars_in_inch)
        if "textindent" in style["paragraphproperties"]:
            first_indent = inch_to_spaces(style["paragraphproperties"]["textindent"], chars_in_inch)
            spaces_to_insert = first_indent
    max_char = inch_to_spaces(page_width, chars_in_inch) - l_marg - r_marg
    # print(max_char)
    # this only deals with a tab at the start of the paragraph
    if "\t" in text[0:3]:
        mat = re.search("\t", text)
        # print(first_indent)
        # print(l_marg)
        # print(mat.start())
        begin_pos = first_indent + l_marg + mat.start()
        # print(begin_pos)
        if "tabstop" in style["paragraphproperties"]:
        # example with 0.5 par indent, 0.5 text indent
        # original string: Q.\tABC
        # formatted:
        # ----------Q.\tABC
        # tabstop at 1.5in
        # ----------Q.---ABC
        # ---------------{start}
            tabs = style["paragraphproperties"]["tabstop"]
            if isinstance(tabs, list):
                tabs = [inch_to_spaces(i, chars_in_inch) for i in tabs]
                tab_index = bisect.bisect_left(tabs, begin_pos)
                tabs = tabs[tab_index]
            else:
                tabs = inch_to_spaces(tabs, chars_in_inch)
        else:
            # just use the python default tab expansion value
            tabs = 8
        # print("tabs")
        # print(tabs)
        if first_indent > 0:
            spaces_to_insert = (tabs - begin_pos) + first_indent
        else:
            spaces_to_insert = (tabs - begin_pos)
    # print("spaces to insert")
    # print(spaces_to_insert)
    # print("max char")
    # print(max_char)
    par_text = steno_wrap_plain(text = text, block_data = block_data, max_char = max_char,
                                tab_space=4, first_line_indent=" " * spaces_to_insert, par_indent = "", starting_line_num=line_num)
    # print(par_text)
    for k, v in par_text.items():
        par_text[k]["text"] = par_text[k]["text"].lstrip(" ") + "\n"
    if list(par_text.keys()):
        par_text[list(par_text.keys())[-1]]["text"] = par_text[list(par_text.keys())[-1]]["text"].rstrip("\n")
    return(par_text)

def format_text(block, style, max_char = 80, line_num = 0):
    # block is QTextBlock
    # max_char fed into function is converted from page width or user setting (line num digits and timestamp digits are "outside of page")
    text = block.text()
    l_marg = 0
    r_marg = 0
    t_marg = 0
    b_marg = 0
    align = "left"
    linespacing = "100%"
    first_indent = 0
    block_data = block.userData().return_all()
    # all measurements converted to spaces, for horizontal, 10 chars per inch, for vertical, 6 chars per inch
    if "paragraphproperties" in style:
        if "marginleft" in style["paragraphproperties"]:
            l_marg = inch_to_spaces(style["paragraphproperties"]["marginleft"])
        if "marginright" in style["paragraphproperties"]:
            r_marg = inch_to_spaces(style["paragraphproperties"]["marginright"])
        if "margintop" in style["paragraphproperties"]:
            t_marg = inch_to_spaces(style["paragraphproperties"]["margintop"], 6)
        if "marginbottom" in style["paragraphproperties"]:
            b_margin = inch_to_spaces(style["paragraphproperties"]["marginbottom"], 6)
        if "linespacing" in style["paragraphproperties"]:
            linespacing = style["paragraphproperties"]["linespacing"]
        if "textalign" in style["paragraphproperties"]:
            align = style["paragraphproperties"]["textalign"]
            # do not support justified text for now
            if align == "justify":
                align = "left"
        if "textindent" in style["paragraphproperties"]:
            first_indent = inch_to_spaces(style["paragraphproperties"]["textindent"])
        # todo: tabstop conversion
    # since plaintext, none of the textproperties apply
    max_char = max_char - l_marg - r_marg
    # this only deals with a tab at the start of the paragraph
    if "\t" in text[0:3] and "tabstop" in style["paragraphproperties"]:
        # example with 0.5 par indent, 0.5 text indent
        # original string: Q.\tABC
        # formatted:
        # ----------Q.\tABC
        # tabstop at 1.5in
        # ----------Q.---ABC
        # ---------------{start}
        tabs = style["paragraphproperties"]["tabstop"]
        mat = re.search("\t", text)
        begin_pos = first_indent + l_marg + mat.start()
        if isinstance(tabs, list):
            tabs = [inch_to_spaces(i) for i in tabs]
            tab_index = bisect.bisect_left(tabs, begin_pos)
            tabs = tabs[tab_index]
        else:
            tabs = inch_to_spaces(tabs)
        # tabs_to_space_pos = inch_to_spaces(tabs)
        spaces_to_insert = (tabs - begin_pos) * " "
        text = re.sub("\t", spaces_to_insert, text, count = 1)
        for i, stroke in enumerate(block_data["strokes"]):
            if "\t" in stroke[2]:
                block_data["strokes"][i][2] = re.sub("\t",  spaces_to_insert, block_data["strokes"][i][2], count = 1)
                break
    par_text = steno_wrap_plain(text = text, block_data = block_data, max_char = max_char,
                                tab_space=4, first_line_indent=" " * (first_indent + l_marg), par_indent = " " * l_marg, starting_line_num=line_num)
    for k, v in par_text.items():
        if align == "center":
            par_text[k]["text"] = par_text[k]["text"].center(max_char)
        elif align == "right":
            par_text[k]["text"] = par_text[k]["text"].rjust(max_char)
        else:
            par_text[k]["text"] = par_text[k]["text"].ljust(max_char)
    if t_marg > 0:
        par_text[line_num+1]["text"] = "\n" * t_marg + par_text[line_num+1]["text"]
    if b_marg > 0:
        par_text[-1]["text"] = par_text[-1]["text"] + "\n" * b_marg
    # decide whether to add extra line(s) due to linespacing, will round to two extra empty lines if over 149%
    line_spaces = int(int(linespacing.replace("%", "")) / 100) - 1
    for k, v in par_text.items():
        par_text[k]["text"] = par_text[k]["text"] + "\n" * line_spaces
    return(par_text)

def steno_wrap_plain(text, block_data, max_char = 80, tab_space = 4, first_line_indent = "", 
                        par_indent = "", timestamp = False, starting_line_num = 0):
    # the -1 in max char is because the rounding is not perfect, might have some lines that just tip over
    wrapped = textwrap.wrap(text, width = max_char - 1, initial_indent= first_line_indent,
                subsequent_indent= par_indent, expand_tabs = False, tabsize = tab_space, replace_whitespace=False)
    begin_pos = 0
    par_dict = {}
    for ind, i in enumerate(wrapped):
        matches = re.finditer(re.escape(i.strip()), text[begin_pos:])
        for i in matches:
            if i.start() >= 0:
                match = i
                break
        end_pos = match.end()
        ## try very desperately to recover
        if end_pos == begin_pos:
            end_pos = begin_pos + len(wrapped[ind]) - 1
        extracted_data = extract_stroke_data(block_data["strokes"], begin_pos, end_pos, copy = True)
        timecodes = [stroke[0] for stroke in extracted_data]
        timecodes.sort()
        begin_pos = match.end()
        par_dict[starting_line_num + ind + 1] = {}
        par_dict[starting_line_num + ind + 1]["text"] = wrapped[ind]
        # par_dict[ind]["line_num"] = starting_line_num + ind + 1
        par_dict[starting_line_num + ind + 1]["time"] = timecodes[0]
    return(par_dict)

def load_odf_styles(path):
    # log.info("Loading ODF style file from %s", str(path))
    style_text = load(path)
    json_styles = {}
    for style in style_text.getElementsByType(Styles)[0].getElementsByType(Style):
        if style.getAttribute("family") != "paragraph":
             continue
        # print(style.getAttribute("name"))
        json_styles[style.getAttribute("name")] = {"family": style.getAttribute("family"), "nextstylename": style.getAttribute("nextstylename"), "defaultoutlinelevel": style.getAttribute("defaultoutlinelevel"), "parentstylename": style.getAttribute("parentstylename")}
        if style.getElementsByType(ParagraphProperties):
            par_prop = style.getElementsByType(ParagraphProperties)[0]
            par_dict = {"textalign": par_prop.getAttribute("textalign"), "textindent": par_prop.getAttribute("textindent"), 
                        "marginleft": par_prop.getAttribute("marginleft"), "marginright": par_prop.getAttribute("marginright"), 
                        "margintop": par_prop.getAttribute("margintop"), "marginbottom": par_prop.getAttribute("marginbottom"), "linespacing": par_prop.getAttribute("linespacing")}
            if par_prop.getElementsByType(TabStops):
                tabstop = []
                for i in par_prop.getElementsByType(TabStop):
                    tabstop.append(i.getAttribute("position"))
                par_dict["tabstop"] = tabstop
            json_styles[style.getAttribute("name")]["paragraphproperties"] = par_dict
        if style.getElementsByType(TextProperties):
            txt_prop = style.getElementsByType(TextProperties)[0]
            txt_dict = {"fontname": txt_prop.getAttribute("fontname"), "fontfamily": txt_prop.getAttribute("fontfamily"), 
                        "fontsize": txt_prop.getAttribute("fontsize"), "fontweight": txt_prop.getAttribute("fontweight"), 
                        "fontstyle": txt_prop.getAttribute("fontstyle"), "textunderlinetype": txt_prop.getAttribute("textunderlinetype"), 
                        "textunderlinestyle": txt_prop.getAttribute("textunderlinestyle")}
            json_styles[style.getAttribute("name")]["textproperties"] = txt_dict
    json_styles = remove_empty_from_dict(json_styles)
    return(json_styles)

def recursive_style_format(style_dict, style, prop = "paragraphproperties"):
    if "parentstylename" in style_dict[style]:
        parentstyle = recursive_style_format(style_dict, style_dict[style]["parentstylename"], prop = prop)
        if prop in style_dict[style]:
            parentstyle.update(style_dict[style][prop])
        return(deepcopy(parentstyle))
    else:
        if prop in style_dict[style]:
            return(deepcopy(style_dict[style][prop]))
        else:
            return({})

def parprop_to_blockformat(par_dict):
    par_format = QTextBlockFormat()
    if "textalign" in par_dict:
        if par_dict["textalign"] == "justify":
            par_format.setAlignment(Qt.AlignJustify)
        elif par_dict["textalign"] == "right":
            par_format.setAlignment(Qt.AlignRight)
        elif par_dict["textalign"] == "center":
            par_format.setAlignment(Qt.AlignHCenter)
        else:
            # set default to left
            par_format.setAlignment(Qt.AlignLeft)
    if "textindent" in par_dict:
        par_format.setTextIndent(in_to_pixel(par_dict["textindent"].replace("in","")))
    if "marginleft" in par_dict:
        par_format.setLeftMargin(in_to_pixel(par_dict["marginleft"].replace("in", "")))
    if "marginright" in par_dict:
        par_format.setRightMargin(in_to_pixel(par_dict["marginright"].replace("in", "")))
    if "marginbottom" in par_dict:
        par_format.setBottomMargin(in_to_pixel(par_dict["marginbottom"].replace("in", "")))
    if "linespacing" in par_dict:
        par_format.setLineHeight(
            float(par_dict["linespacing"].replace("%", "")),
            QTextBlockFormat.ProportionalHeight
        )
    if "tabstop" in par_dict:
        tab_list = par_dict["tabstop"]
        blocktabs = []
        if isinstance(tab_list, str):
            tab_list = [tab_list]
        for i in tab_list:
            tab_pos = in_to_pixel(i.replace("in", ""))
            blocktabs.append(QTextOption.Tab(tab_pos, QTextOption.LeftTab))
        par_format.setTabPositions(blocktabs)
    return(par_format)

def txtprop_to_textformat(txt_dict):
    txt_format = QTextCharFormat()
    if "fontfamily" in txt_dict:
        potential_font = QFont(txt_dict["fontfamily"])
    else:
        # if no font, then set a default
        potential_font = QFont("Courier New")
    if "fontsize" in txt_dict:
        potential_font.setPointSize(int(float(txt_dict["fontsize"].replace("pt", ""))))
    else:
        # must have a font size
        potential_font.setPointSize(12)
    if "fontweight" in txt_dict and txt_dict["fontweight"] == "bold":
        # boolean for now, odf has weights and so does qt
        potential_font.setBold(True)
    if "fontstyle" in txt_dict and txt_dict["fontstyle"] == "italic":
        potential_font.setItalic(True)
    if "textunderlinetype" in txt_dict and txt_dict["textunderlinestyle"] == "solid":
        potential_font.setUnderline(True)
    txt_format.setFont(potential_font, QTextCharFormat.FontPropertiesAll)
    return(txt_format)
