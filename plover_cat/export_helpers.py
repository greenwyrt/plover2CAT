import bisect
import re 
from PySide6.QtGui import QTextBlockFormat, QFont, QTextCharFormat, QTextOption
from PySide6.QtCore import Qt
from plover_cat.steno_objects import *
from plover_cat.helpers import *
from copy import deepcopy
from odf.style import (Style, TextProperties, ParagraphProperties, FontFace, PageLayout, 
PageLayoutProperties, MasterPage, TabStops, TabStop, GraphicProperties, Header, Footer)

def format_odf_text(block_data, style, chars_in_inch, page_width, line_num = 0):
    """Format a string into wrapped lines for ODF.

    This uses ``steno_wrap_ODF`` and does additional formatting to wrapped
    lines by converting necessary styling parameters.

    :param block_data: an ``element_collection``
    :param dict style: styling parameters in dict
    :param int chars_in_inch: approximate number of characters in inch for selected style font
    :param page_width: page width of ODF document, in inches
    :param int line_num: line number for starting line
    :return: dict of dicts ``{line_number: {line_text, line_timestamp}}``
    """
    # block is QTextBlock
    # max_char fed into function is converted from page width or user setting (line num digits and timestamp digits are "outside of page")
    text = block_data.to_text()
    l_marg = 0
    r_marg = 0
    first_indent = 0
    # block_data = deepcopy(block.userData()["strokes"])
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
        if first_indent > 0:
            spaces_to_insert = (tabs - begin_pos) + first_indent
        else:
            spaces_to_insert = (tabs - begin_pos)
    par_text = steno_wrap_odf(block_data = block_data, max_char = max_char,
                                tab_space=4, first_line_indent=" " * spaces_to_insert, par_indent = "", starting_line_num=line_num)
    # print(par_text)
    for k, v in par_text.items():
        # erase whitespace at front since odf formatting is separate
        par_text[k]["text"][0].data = par_text[k]["text"][0].data.lstrip(" ")
        # each item line should end with \n except last
        if not par_text[k]["text"][-1].endswith("\n"):
            par_text[k]["text"][-1].data = par_text[k]["text"][-1].data + ("\n")
    if list(par_text.keys()):
        # last line of paragraph should not have a "\n" char, new paragraph is done through odf elements
        par_text[list(par_text.keys())[-1]]["text"][-1].data = par_text[list(par_text.keys())[-1]]["text"][-1].data.rstrip("\n")
    return(par_text)

def format_text(block_data, style, max_char = 80, line_num = 0):
    """Format a string into wrapped lines for text.

    This uses ``steno_wrap_plain`` and does additional formatting to wrapped
    lines by converting styling parameters to padding space characters to make
    formatted text lines.

    :param block_data: an ``element_collection``
    :param dict style: styling parameters in dict
    :param int max_char: maximum characters in a line
    :param int line_num: line number for starting line
    :return: dict of dicts ``{line_number: {line_text, line_timestamp}}``
    """
    # block is QTextBlock
    # max_char fed into function is converted from page width or user setting (line num digits and timestamp digits are "outside of page")
    text = block_data.to_text()
    l_marg = 0
    r_marg = 0
    t_marg = 0
    b_marg = 0
    align = "left"
    linespacing = "100%"
    first_indent = 0
    # print(block_data)
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
        block_data.replace_initial_tab(spaces_to_insert)
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

def format_srt_text(block_data, line_num = 0, audiostarttime = "", audioendtime = ""):
    """Wrap steno data for SRT.

    :param block_data: an ``element_collection`` for a paragraph
    :param int line_num: starting line number
    :param audiostarttime: paragraph's ``audiostarttime``
    :param audioendtime: paragraph's ``audioendtime``
    :return: dict of dicts ``{line_number: {line_text, line_timestamp}}``
    """
    par_text = steno_wrap_srt(block_data, max_char = 47, starting_line_num = line_num)
    # line_times = []
    # if audiostarttime and audioendtime:
    #     for line, data in par_txt.items():
    #         line_times.append(data["starttime"])
    #         line_times.append(data["endtime"])
    #     if all([t >= audiostarttime and t <= audioendtime for t in line_times]):
    #         return(par_text)
    #     else:
    #         audiostarttime = hours_to_ms(audiostarttime)
    #         audioendtime = hours_to_ms(audioendtime)
    #         # not complete
    return(par_text)

def steno_wrap_plain(text, block_data, max_char = 80, tab_space = 4, first_line_indent = "", 
                        par_indent = "", starting_line_num = 0):
    """Wrap steno data properly for text.
    
    See code to compare for differences with ``steno_wrap_odf`` and ``steno_wrap_srt``.

    :param str text: text to wrap
    :param block_data: an ``element_collection`` for a paragraph
    :param int max_char: maximum number of characters per line
    :param int tab_space: how many spaces should a tab character be converted into
    :param str first_line_indent: string to place at beginning of first line
    :param str par_indent: string to place at beginning of every line except first
    :param int starting_line_num: line number to add to beginning of each line
    :return: dict of dicts ``{line_number: {line_text, line_timestamp}}``
    
    """
    # the -1 in max char is because the rounding is not perfect, might have some lines that just tip over
    # uses text string instead of block_data because text has pre-expanded tabs 
    wrapped = textwrap.wrap(text, width = max_char - 1, initial_indent= first_line_indent,
                subsequent_indent= par_indent, expand_tabs = False, tabsize = tab_space, replace_whitespace=False)
    begin_pos = 0
    par_dict = {}
    for ind, i in enumerate(wrapped):
        matches = block_data.extract_steno(begin_pos, len(block_data)).search_text(i.strip())
        # matches = re.finditer(re.escape(i.strip()), text[begin_pos:])
        for i in matches:
            if i.start() >= 0:
                match = i
                break
        end_pos = match.end()
        ## try very desperately to recover
        if end_pos == begin_pos:
            end_pos = begin_pos + len(wrapped[ind]) - 1
        line_time = block_data.extract_steno(begin_pos, end_pos).collection_time()
        begin_pos = match.end()
        par_dict[starting_line_num + ind + 1] = {"text": wrapped[ind], "time": line_time}
    return(par_dict)

def steno_wrap_odf(block_data, max_char = 80, tab_space = 4, first_line_indent = "", 
                        par_indent = "", starting_line_num = 0):
    """Wrap steno data properly for ODF.

    Compare with ``steno_wrap_plain``.
    
    :param block_data: an ``element_collection`` for a paragraph
    :param int max_char: maximum number of characters per line
    :param int tab_space: how many spaces should a tab character be converted into
    :param str first_line_indent: string to place at beginning of first line
    :param str par_indent: string to place at beginning of every line except first
    :param int starting_line_num: line number to add to beginning of each line
    :return: dict of dicts ``{line_number: {line_text, line_timestamp}}``
    
    """
    # the -1 in max char is because the rounding is not perfect, might have some lines that just tip over
    wrapper = steno_wrapper(width = max_char - 1, initial_indent= first_line_indent,
                subsequent_indent= par_indent, expand_tabs = False, tabsize = tab_space, replace_whitespace=False)
    wrapped = wrapper.wrap(text = block_data)
    begin_pos = 0
    par_dict = {}
    for ind, i in enumerate(wrapped):
        line_time = element_collection(i).collection_time()
        par_dict[starting_line_num + ind + 1] = {"text": wrapped[ind], "time": line_time}
    return(par_dict)

def steno_wrap_srt(block_data, max_char = 47, tab_space = 0, first_line_indent = "", 
                        par_indent = "", starting_line_num = 0):
    """Wrap steno data properly, but with audio timestamps.

    Compare to ``steno_wrap_odf``
    
    :param block_data: an ``element_collection`` for a paragraph
    :param int max_char: maximum number of characters per line
    :param int tab_space: how many spaces should a tab character be converted into
    :param str first_line_indent: string to place at beginning of first line
    :param str par_indent: string to place at beginning of every line except first
    :param int starting_line_num: line number to add to beginning of each line
    :return: dict of dicts ``{line_number: {line_text, starttime, endtime}}``
    
    """                        
    # change from other wrapper here, tabs are expanded into 0 spaces
    wrapper = steno_wrapper(width = max_char - 1, initial_indent= first_line_indent,
                subsequent_indent= par_indent, expand_tabs = True, tabsize = tab_space, replace_whitespace=False)
    wrapped = wrapper.wrap(text = block_data)
    begin_pos = 0
    par_dict = {}
    for ind, i in enumerate(wrapped):
        ec = element_collection(i)
        start_time = ec.audio_time()
        end_time = ec.audio_time(reverse = True)
        par_dict[starting_line_num + ind + 1] = {"text": wrapped[ind], "starttime": start_time, "endtime": end_time}
    return(par_dict)

def load_odf_styles(path):
    """Extract styles from ODT file and convert supported parameters to par and text style dicts."""
    log.debug(f"Loading ODF style file from {str(path)}")
    style_text = load(path)
    json_styles = {}
    for style in style_text.getElementsByType(Styles)[0].getElementsByType(Style):
        if style.getAttribute("family") != "paragraph":
             continue
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
    """Get full style par/text format dict if style inherits from another."""
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
    """Take dict of paragraph attributes, return ``QTextBlockFormat``."""
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
            QTextBlockFormat.ProportionalHeight.value
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
    """Take dict of text attributes, return ``QTextCharFormat``."""
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

