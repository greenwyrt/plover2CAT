import pathlib
import xml.etree.ElementTree as ET
import html
from datetime import datetime
from dulwich.repo import Repo
from math import trunc
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFontMetrics
from time import sleep
from plover import log
from plover_cat.helpers import save_json, ms_to_hours, return_commits, inch_to_spaces, write_command
from plover_cat.steno_objects import *
from plover_cat.rtf_parsing import *
from plover_cat.export_helpers import *
from odf.opendocument import OpenDocumentText, load
from odf.office import FontFaceDecls, Styles
from odf.style import (Style, TextProperties, ParagraphProperties, FontFace, PageLayout, 
PageLayoutProperties, MasterPage, TabStops, TabStop, GraphicProperties, Header, Footer)
from odf.text import H, P, Span, Tab, LinenumberingConfiguration, PageNumber, UserFieldDecls, UserFieldDecl, UserFieldGet
from odf.teletype import addTextToElement
from odf.draw import Frame, TextBox, Image

class documentWorker(QObject):
    """Create exported files.
    
    Worker to create export files, with
    each ``save_*`` function creating one specific file format.
    
    :param dict document: transcript data of form ``{"par_number": {paragraph data}, ...}``
    :param str path: path for export file
    :param styles: dict of style parameters
    :param config: transcript configuration
    :param home_dir: transcript home directory
    """
    progress = pyqtSignal(int)
    """Signal sent progress based on export of paragraph."""
    finished = pyqtSignal()
    """Signal sent when export is finished."""
    def __init__(self, document, path, config, styles, user_field_dict, home_dir):
        QObject.__init__(self)  
        self.document = document
        self.path = path
        self.styles = styles
        self.config = config
        self.user_field_dict = user_field_dict
        self.home_dir = home_dir
    def save_ascii(self):
        """Export to formatted ASCII."""
        ef = element_factory()
        doc_lines = {}
        line = -1
        for block_num, block_data in self.document.items():
            style_name = block_data["style"]
            block_style = {
                    "paragraphproperties": recursive_style_format(self.styles, style_name),
                    "textproperties": recursive_style_format(self.styles, style_name, prop = "textproperties")
                }
            page_hspan = inch_to_spaces(self.config["page_width"]) - inch_to_spaces(self.config["page_left_margin"]) - inch_to_spaces(self.config["page_right_margin"])
            page_vspan = inch_to_spaces(self.config["page_height"], 6) - inch_to_spaces(self.config["page_top_margin"], 6) - inch_to_spaces(self.config["page_bottom_margin"], 6)
            if self.config["page_max_char"] != 0:
                page_hspan = self.config["page_max_char"]
            if self.config["page_max_line"] != 0:
                page_vspan = self.config["page_max_line"]
            el_list = element_collection([ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in block_data["strokes"]])
            par_dict = format_text(el_list, block_style, page_hspan, line)
            doc_lines.update(par_dict)
            line = line + len(par_dict)
            self.progress.emit(int(block_num))
        if self.config["page_line_numbering"]:
            page_line_num = 1
            for key, line in doc_lines.items():
                if page_line_num > page_vspan:
                    page_line_num = 1
                num_line = str(page_line_num).rjust(2)
                text_line = doc_lines[key]["text"]
                doc_lines[key]["text"] = f"{num_line} {text_line}"
                page_line_num += 1
        if self.config["page_timestamp"]:
            for key, line in doc_lines.items():
                text_line = doc_lines[key]["text"]
                line_time = datetime.strptime(line["time"], "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')
                doc_lines[key]["text"] = f"{line_time} {text_line}"
        file_path = pathlib.Path(self.path)
        with open(file_path, "w", encoding="utf-8") as f:
            for key, line in doc_lines.items():
                if key % page_vspan == 0:
                    # header
                    quotient, mod = divmod(key, page_vspan)
                    header_left = self.config["header_left"].replace("%p", str(quotient + 1))
                    header_center = self.config["header_center"].replace("%p", str(quotient + 1))
                    header_right = self.config["header_right"].replace("%p", str(quotient + 1))
                    header_text = header_center.center(page_hspan)
                    header_text = header_left + header_text[len(header_left):]
                    header_text = header_text[:(len(header_text)-len(header_right))] + header_right
                    f.write(f"{header_text}\n")
                text_line = line["text"]
                f.write(f"{text_line}\n")
                if key % page_vspan == (page_vspan - 1):
                    quotient, mod = divmod(key, page_vspan)
                    footer_left = self.config["footer_left"].replace("%p", str(quotient + 1))
                    footer_center = self.config["footer_center"].replace("%p", str(quotient + 1))
                    footer_right = self.config["footer_right"].replace("%p", str(quotient + 1))
                    footer_text = footer_center.center(page_hspan)
                    footer_text = footer_left + footer_text[len(footer_left):]
                    footer_text = footer_text[:(len(footer_text)-len(footer_right))] + footer_right
                    f.write(f"{footer_text}\n")  
        self.finished.emit()      
    def save_html(self):
        """Export to formatted HTML."""
        ef = element_factory()
        doc_lines = {}
        line = -1
        for block_num, block_data in self.document.items():
            style_name = block_data["style"]
            block_style = {
                    "paragraphproperties": recursive_style_format(self.styles, style_name),
                    "textproperties": recursive_style_format(self.styles, style_name, prop = "textproperties")
                }
            page_hspan = inch_to_spaces(self.config["page_width"]) - inch_to_spaces(self.config["page_left_margin"]) - inch_to_spaces(self.config["page_right_margin"])
            page_vspan = inch_to_spaces(self.config["page_height"], 6) - inch_to_spaces(self.config["page_top_margin"], 6) - inch_to_spaces(self.config["page_bottom_margin"], 6)
            if self.config["page_max_char"] != 0:
                page_hspan = self.config["page_max_char"]
            if self.config["page_max_line"] != 0:
                page_vspan = self.config["page_max_line"]
            el_list = element_collection([ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in block_data["strokes"]])
            par_dict = format_text(el_list, block_style, page_hspan, line)
            doc_lines.update(par_dict)
            line = line + len(par_dict)
            self.progress.emit(int(block_num))
        if self.config["page_line_numbering"]:
            page_line_num = 1
            for key, line in doc_lines.items():
                if page_line_num > page_vspan:
                    page_line_num = 1
                num_line = str(page_line_num).rjust(2)
                text_line = doc_lines[key]["text"]
                doc_lines[key]["text"] = f"{num_line} {text_line}"
                page_line_num += 1
        if self.config["page_timestamp"]:
            for key, line in doc_lines.items():
                text_line = doc_lines[key]["text"]
                line_time = datetime.strptime(line["time"], "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')
                doc_lines[key]["text"] = f"{line_time} {text_line}"
        file_path = pathlib.Path(self.path)
        root = ET.Element("html")
        head = ET.SubElement(root, "head")
        body = ET.SubElement(root, "body")
        pre = ET.SubElement(body, "pre")
        for_html = []
        for k, v in doc_lines.items():
            if k % page_vspan == 0:
                # header
                quotient, mod = divmod(k, page_vspan)
                header_left = self.config["header_left"].replace("%p", str(quotient + 1))
                header_center = self.config["header_center"].replace("%p", str(quotient + 1))
                header_right = self.config["header_right"].replace("%p", str(quotient + 1))
                header_text = header_center.center(page_hspan)
                header_text = header_left + header_text[len(header_left):]
                header_text = header_text[:(len(header_text)-len(header_right))] + header_right
                for_html.append(header_text)
            for_html.append(doc_lines[k]["text"])
            if k % page_vspan == (page_vspan - 1):
                quotient, mod = divmod(k, page_vspan)
                footer_left = self.config["footer_left"].replace("%p", str(quotient + 1))
                footer_center = self.config["footer_center"].replace("%p", str(quotient + 1))
                footer_right = self.config["footer_right"].replace("%p", str(quotient + 1))
                footer_text = footer_center.center(page_hspan)
                footer_text = footer_left + footer_text[len(footer_left):]
                footer_text = footer_text[:(len(footer_text)-len(footer_right))] + footer_right
                for_html.append(footer_text)
        for_html_string = "\n".join(for_html)
        pre.text = for_html_string
        html_string = ET.tostring(element = root, encoding = "unicode", method = "html")
        with open(file_path, "w+", encoding="utf-8") as f:
            f.write(html_string)
        self.finished.emit()
    def save_odf(self):
        """Export to ODF Text Document."""
        ef = element_factory()
        set_styles = self.styles
        if self.config["style"].endswith(".json"):
            textdoc = OpenDocumentText()
            # set page layout
            automatic_styles = textdoc.automaticstyles
            page_layout = PageLayout(name = "Transcript")
            page_layout_dict = {"pagewidth": "%.2fin" % self.config["page_width"], 
                                "pageheight": "%.2fin" % self.config["page_height"], "printorientation": "portrait",
                                "margintop": "%.2fin" % self.config["page_top_margin"], 
                                "marginbottom": "%.2fin" % self.config["page_bottom_margin"], 
                                "marginleft":  "%.2fin" % self.config["page_left_margin"],
                                "marginright": "%.2fin" % self.config["page_right_margin"], "writingmode": "lr-tb"}
            if self.config["page_max_line"] != 0:
                page_layout_dict["layoutgridlines"] = str(self.config["page_max_line"])
                page_layout_dict["layoutgridmode"] = "line"
            # log.debug(page_layout_dict)
            page_layout.addElement(PageLayoutProperties(attributes=page_layout_dict))
            automatic_styles.addElement(page_layout) 
            master_style = textdoc.masterstyles
            master_page = MasterPage(name = "Standard", pagelayoutname = "Transcript")
            master_style.addElement(master_page)             
            # set paragraph styles
            s = textdoc.styles
            if self.config["page_line_numbering"]:
                line_style = Style(name = "Line_20_numbering", displayname = "Line Numbering", family = "text")
                s.addElement(line_style)
                lineconfig_style = LinenumberingConfiguration(stylename = "Line_20_numbering", restartonpage = "true", offset = "0.15in", 
                                                                numformat = "1", numberposition = "left", increment = str(self.config["page_linenumbering_increment"]))
                s.addElement(lineconfig_style)
            fonts = textdoc.fontfacedecls
            # go through every style, get all font declarations, set the fontfamily as fontname
            doc_fonts = []
            for k, v in set_styles.items():
                if v.get("textproperties"):
                    doc_fonts.append(v["textproperties"]["fontfamily"])
            # here, the fontfamily gets single quotes because it won't work when font string has spaces
            # default font is set as modern, with fixed pitch
            for style_font in doc_fonts:
                fonts.addElement(FontFace(attributes={"name": style_font, "fontfamily": "'" + style_font + "'", "fontfamilygeneric": "modern", "fontpitch": "fixed"}))
            # loop through every element of style json, use try-except to still get through to odf even if some attributes are not correct
            for name, style in set_styles.items():
                style_name = name
                new_style = Style(name = style_name, family = "paragraph")
                if "parentstylename" in style:
                    new_style.setAttribute("parentstylename", style["parentstylename"])
                if "nextstylename" in style:
                    new_style.setAttribute("nextstylename", style["nextstylename"])
                if "defaultoutlinelevel" in style:
                    new_style.setAttribute("defaultoutlinelevel", style["defaultoutlinelevel"])      
                if "textproperties" in style:
                    text_prop = TextProperties()
                    for attribute, value in style["textproperties"].items():
                        # with loop, can try each attribute and skip if doesn't work
                        # better than stuffing all attributes in as a dict
                        try:
                            text_prop.setAttribute(attribute, value)
                        except:
                            pass
                    new_style.addElement(text_prop)
                if "paragraphproperties" in style:
                    par_prop = ParagraphProperties()
                    for attribute, value in style["paragraphproperties"].items():
                        try:
                            par_prop.setAttribute(attribute, value)
                        except:
                            pass
                    if "tabstop" in style["paragraphproperties"]:
                        tab_list = style["paragraphproperties"]["tabstop"]
                        style_tab = TabStops()
                        if isinstance(tab_list, str):
                            tab_list = [tab_list]
                        for i in tab_list:
                            true_tab = TabStop(position = i)
                            style_tab.addElement(true_tab)
                        par_prop.addElement(style_tab)
                    new_style.addElement(par_prop)
                for attribute, value in style.items():
                    if attribute == "textproperties" or "paragraphproperties":
                        pass
                    try:
                        new_style.setAttribute(attribute, value)
                    except:
                        pass
                new_style.attributes
                s.addElement(new_style)
        else:
            template = pathlib.Path(self.home_dir) / self.config["style"]
            textdoc = load(template)
            s = textdoc.styles
            master_page = textdoc.getElementsByType(MasterPage)        
        frame_style = Style(name = "Frame", family = "graphic")
        frame_prop = GraphicProperties(attributes = {"verticalpos": "middle", "verticalrel": "char", "horizontalpos": "from-left", "horizontalrel": "paragraph", "opacity": "0%"})
        frame_style.addElement(frame_prop)
        s.addElement(frame_style)
        doc_lines = {}
        line = -1
        page_width = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("pagewidth")
        page_height = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("pageheight")
        page_lmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("marginleft")
        page_rmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("marginright")
        page_tmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("margintop")
        page_bmarg = textdoc.getElementsByType(PageLayoutProperties)[0].getAttribute("marginbottom")
        text_width = float(page_width.replace("in", "")) - float(page_lmarg.replace("in", "")) - float(page_rmarg.replace("in", ""))
        text_height = float(page_height.replace("in", "")) - float(page_tmarg.replace("in", "")) - float(page_bmarg.replace("in", ""))    
        for block_num, block_data in self.document.items():
            style_name = block_data["style"]
            block_style = {
                    "paragraphproperties": recursive_style_format(self.styles, style_name),
                    "textproperties": recursive_style_format(self.styles, style_name, prop = "textproperties")
                }
            txt_format = txtprop_to_textformat(block_style["textproperties"])
            font_metrics = QFontMetrics(txt_format.font())
            chars_in_inch = round(1 / pixel_to_in(font_metrics.averageCharWidth()))
            height_in_inch = round(1 / pixel_to_in(font_metrics.lineSpacing()))
            page_hspan = inch_to_spaces(text_width, chars_in_inch)
            page_vspan = inch_to_spaces(text_height, height_in_inch)
            if self.config["page_max_char"] != 0:
                if page_vspan > self.config["page_max_char"]:
                    text_width = self.config["page_max_char"] / chars_in_inch
            el_list = element_collection([ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in block_data["strokes"]])
            par_dict = format_odf_text(el_list, block_style, chars_in_inch, text_width, line)
            doc_lines.update(par_dict)
            line = line + len(par_dict)
            if not block_data["style"]:
                log.debug("Paragraph has no style, setting to first style %s" % next(iter(set_styles)))
                par_block = P(stylename = next(iter(set_styles)))
            else:
                if "defaultoutlinelevel" in set_styles[block_data["style"]]:
                    par_block = H(stylename = block_data["style"], outlinelevel = set_styles[block_data["style"]]["defaultoutlinelevel"])
                else:
                    par_block = P(stylename = block_data["style"])
            # this function is important to respect \t and other whitespace properly. 
            for k, v in par_dict.items():
                # the new line causes an automatic line break
                if self.config["page_timestamp"]:
                    line_time = par_dict[k]["time"]
                    time_text = datetime.strptime(line_time, "%Y-%m-%dT%H:%M:%S.%f").strftime('%H:%M:%S')
                    line_frame = Frame(attributes = {"stylename": "Frame", "anchortype": "char", "x": "-1.5in", "width": "0.9in"})
                    line_textbox = TextBox()
                    line_frame.addElement(line_textbox)
                    line_textbox.addElement(P(text = time_text, stylename = next(iter(set_styles))))
                    par_block.addElement(line_frame)
                for el in v["text"]:
                    el.to_odt(par_block, textdoc)
            textdoc.text.addElement(par_block)
            self.progress.emit(int(block_num))
        header = Header()
        header_text = self.config["header_left"] + "\t" + self.config["header_center"] + "\t" + self.config["header_right"]
        header_par = P(stylename = "Header_20_Footer")
        if "%p" in header_text:
            split_htext = header_text.split("%p")
            for i in split_htext:
                addTextToElement(header_par, i)
                if i != split_htext[-1]:
                    header_par.addElement(PageNumber(selectpage = "current"))
        else:
            addTextToElement(header_par, header_text)
        header.addElement(header_par)
        footer = Footer()
        footer_text = self.config["footer_left"] + "\t" + self.config["footer_center"] + "\t" + self.config["footer_right"]
        footer_par = P(stylename = "Header_20_Footer")
        if "%p" in footer_text:
            split_ftext = footer_text.split("%p")
            for i in split_ftext:
                addTextToElement(footer_par, i)
                if i != split_ftext[-1]:
                    footer_par.addElement(PageNumber(selectpage = "current"))
        else:
            addTextToElement(footer_par, footer_text)
        footer.addElement(footer_par)
        master_page.addElement(header)
        master_page.addElement(footer)
        hf_style = Style(name = "Header_20_Footer", family = "paragraph", parentstylename = next(iter(set_styles)))
        hf_properties = ParagraphProperties(numberlines = "false")
        hf_tabstops = TabStops()
        hf_tabstops.addElement(TabStop(position = "%.2fin" % (trunc(text_width)/2)))
        hf_tabstops.addElement(TabStop(position = "%.2fin" % trunc(text_width)))
        hf_properties.addElement(hf_tabstops)
        hf_style.addElement(hf_properties)
        s.addElement(hf_style)
        textdoc.save(self.path)
        self.finished.emit()
    def save_plain_ascii(self):
        """Export to plain text."""
        ef = element_factory() 
        wrapped_text = []
        for block_num, block_data in self.document.items():
            el_list = element_collection([ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in block_data["strokes"]])
            wrapped_text += textwrap.wrap(el_list.to_text())
        self.progress.emit(int(block_num))
        page_number = 1
        max_lines = 25 # this could be adjustable
        doc_lines = []
        for i in range(0, len(wrapped_text), max_lines):
            doc_lines += [f'{page_number:04}']
            page_number +=1
            # padding space, column 2 is start of line number (left justified), column 7 is start of text
            # <space> number{1,2} [space]{3,4}
            doc_lines += [str(line_num).ljust(5).rjust(6) + text for line_num, text in zip(range(1, max_lines), wrapped_text[i: i + max_lines])]
        file_path = pathlib.Path(self.path)
        with open(file_path, "w", encoding="utf-8") as f:
            for line in doc_lines:
                f.write(f"{line}\n") 
        self.finished.emit()       
    def save_rtf(self):
        """Export to RTF file with RTF/CRE."""
        ef = element_factory()
        font_list = []
        for k, v in self.styles.items():
            if "textproperties" in v and "fontfamily" in v["textproperties"]:
                if v["textproperties"]["fontfamily"]:
                    font_list.append(v["textproperties"]["fontfamily"])
                    v["f"] = font_list.index(v["textproperties"]["fontfamily"])
                else:
                    font_list.append(v["textproperties"]["fontfamily"])
                    v["f"] = len(font_list) - 1
        style_string = ""
        style_names = [sname for sname, data in self.styles.items()]                            
        for i, k in enumerate(style_names):
            self.styles[k]["styleindex"] = str(i)
        for sname, v in self.styles.items():
            if "nextstylename" in v:
                v["snext"] = str(style_names.index(v["nextstylename"]))
            if "parentstylename" in v:
                v["sbasedon"] = str(style_names.index(v["parentstylename"]))
            rtf_par_string = ""
            if "paragraphproperties" in v:
                par_dict = v["paragraphproperties"]
                if "marginleft" in par_dict:
                    rtf_par_string += write_command("li", value = in_to_twip(par_dict["marginleft"]))
                if "marginright" in par_dict:
                    rtf_par_string += write_command("ri", value = in_to_twip(par_dict["marginright"]))
                if "textindent" in par_dict:
                    rtf_par_string += write_command("fi", value = in_to_twip(par_dict["textindent"]))
                if "textalign" in par_dict:
                    if par_dict["textalign"] == "left":
                        rtf_par_string += write_command("ql")
                    if par_dict["textalign"] == "right":
                        rtf_par_string += write_command("qr")
                    if par_dict["textalign"] == "justify":
                        rtf_par_string += write_command("qj")
                    if par_dict["textalign"] == "center":
                        rtf_par_string += write_command("qc")
                if "margintop" in par_dict:
                    rtf_par_string += write_command("sb", value = in_to_twip(par_dict["margintop"]))
                if "marginbottom" in par_dict:
                    rtf_par_string += write_command("sa", value = in_to_twip(par_dict["marginbottom"]))
                if "tabstop" in par_dict:
                    if isinstance(par_dict["tabstop"], str):
                        tabstop = [par_dict["tabstop"]]
                    else:
                        tabstop = par_dict["tabstop"]
                    for i in tabstop:
                        rtf_par_string += write_command("tx", value = in_to_twip(i))
            v["rtf_par_style"] = rtf_par_string
            rtf_text_string = ""
            if "textproperties" in v:
                txt_dict = v["textproperties"]
                # remember that fonts were numbered already
                if "f" in v:
                    rtf_text_string += write_command("f", value = str(v["f"]))
                if "fontsize" in txt_dict:
                    rtf_text_string += write_command("fs", value = int(float(txt_dict["fontsize"].replace("pt", ""))) * 2)
                if "fontstyle" in txt_dict:
                    rtf_text_string += write_command("i")
                if "fontweight" in txt_dict:
                    rtf_text_string += write_command("b")
                if "textunderlinetype" in txt_dict:
                    rtf_text_string += write_command("ul")
            v["rtf_txt_style"] = rtf_text_string
        fonttbl_string = ""
        for ind, font in enumerate(font_list):
            font_string = "{" + write_command("f", value = str(ind)) +  write_command("fmodern", text = font) + ";}"
            fonttbl_string += font_string + "\n"
        stylesheet_string = ""
        for k, v in self.styles.items():
            single_style = ""
            single_style += write_command("s", value = v["styleindex"])
            if "snext" in v:
                single_style += write_command("snext", value = v["snext"])
            if "sbasedon" in v:
                single_style += write_command("sbasedon", value = v["sbasedon"])
            single_style += v["rtf_par_style"]
            stylesheet_string += "{" + single_style + " " + k + ";}\n"
        steno_string = []
        stroke_count = 0
        for block_num, block_data in self.document.items():
            steno_string.append("\n")
            steno_string.append(write_command("par"))
            steno_string.append(write_command("pard"))
            if not block_data["style"]:
                log.debug("Paragraph has no style, setting to first style %s" % next(iter(self.styles)))
                par_style = next(iter(self.styles))
            else:
                par_style = block_data["style"]                                
            par_style_string = write_command("s", value = self.styles[par_style]["styleindex"])
            par_style_string += self.styles[par_style]["rtf_par_style"]
            par_style_string += self.styles[par_style]["rtf_txt_style"]
            steno_string.append(par_style_string)
            # strokes = block_data["strokes"]
            el_list = element_collection([ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in block_data["strokes"]])
            stroke_count += el_list.stroke_count()
            steno_string.append(el_list.to_rtf())
            self.progress.emit(int(block_num))
        document_string = []
        document_string.append("{")
        # meta
        document_string.append(write_command("rtf", value = 1))
        document_string.append(write_command("ansi"))
        document_string.append(write_command("deff", value = 0)) 
        commit = return_commits(Repo(self.home_dir)) 
        last_commit = datetime.strptime(commit[-1][1], "%a %b %d %Y %H:%M:%S")
        recent_commit = datetime.strptime(commit[0][1], "%a %b %d %Y %H:%M:%S")
        commits = f'{len(commit):03}'
        document_string.append(write_command("cxrev", value = commits, visible = False, group = True))
        document_string.append(write_command("cxtranscript", visible = False, group = True))
        document_string.append(write_command("cxsystem", "Plover2CAT", visible = False, group = True))
        info_string = []
        create_string = write_command("yr", value = last_commit.year) + write_command("mo", value = last_commit.month) + write_command("dy", value = last_commit.day)
        backup_string = write_command("yr", value = recent_commit.year) + write_command("mo", value = recent_commit.month) + write_command("dy", value = recent_commit.day)
        page_vspan = inch_to_spaces(self.config["page_height"], 6) - inch_to_spaces(self.config["page_top_margin"], 6) - inch_to_spaces(self.config["page_bottom_margin"], 6)
        if self.config["page_max_line"] != 0:
            page_vspan = int(self.config["page_max_line"])
        info_string.append(write_command("cxnoflines", value = page_vspan))
        # cxlinex and cxtimex is hardcoded as it is also harcoded in odf
        # based on rtf spec, confusing whether left text margin, or left page margin
        info_string.append(write_command("creatim", value = create_string, group = True))
        info_string.append(write_command("buptim", value = backup_string, group = True))
        info_string.append(write_command("cxlinex", value = int(in_to_twip(-0.15))))
        info_string.append(write_command("cxtimex", value = int(in_to_twip(-1.5))))
        info_string.append(write_command("cxnofstrokes", value = stroke_count))
        document_string.append(write_command("info", "".join(info_string), group = True))
        document_string.append(write_command("fonttbl", text = fonttbl_string, group = True))
        document_string.append(write_command("colortbl", value = ";", group = True))
        document_string.append(write_command("stylesheet", text = stylesheet_string, group = True))
        document_string.append(write_command("paperw", value = in_to_twip(self.config["page_width"])))
        document_string.append(write_command("paperh", value = in_to_twip(self.config["page_height"])))
        document_string.append(write_command("margl", value = in_to_twip(self.config["page_left_margin"])))
        document_string.append(write_command("margr", value = in_to_twip(self.config["page_right_margin"])))
        document_string.append(write_command("margt", value = in_to_twip(self.config["page_top_margin"])))
        document_string.append(write_command("margb", value = in_to_twip(self.config["page_bottom_margin"])))
        document_string.append("".join(steno_string))
        document_string.append("}")
        with open(self.path, "w", encoding = "utf8") as f:
            f.write("".join(document_string))
        self.finished.emit()
    def save_srt(self):
        """Export to SRT captions."""
        ef = element_factory()
        line_num = 1
        doc_lines = []
        log.debug(f"Exporting in SRT to {self.path}")
        for block_num, block_data in self.document.items():
            if "audioendtime" not in block_data:
                if str(int(block_num) + 1) in self.document and "audiostarttime" in self.document[str(int(block_num) + 1)]:
                    block_data["audioendtime"] = self.document[str(int(block_num) + 1)]["audiostarttime"]
                else:
                    block_data["audioendtime"] = None
            el_list = element_collection([ef.gen_element(element_dict = i, user_field_dict = self.user_field_dict) for i in block_data["strokes"]])
            par_dict = format_srt_text(el_list, line_num = line_num, audiostarttime = block_data["audiostarttime"], audioendtime = block_data["audioendtime"])
            line_num += len(par_dict)
            for k, v in par_dict.items():
                doc_lines += [k]
                doc_lines += [ms_to_hours(v["starttime"]).replace(".", ",") + " --> " + ms_to_hours(v["endtime"]).replace(".", ",")]
                doc_lines += ["".join([el.to_text() for el in v["text"]])]
                doc_lines += [""]
            self.progress.emit(int(block_num))
        file_path = pathlib.Path(self.path)
        with open(file_path, "w", encoding="utf-8") as f:
            for line in doc_lines:
                f.write(f"{line}\n")
        self.finished.emit()