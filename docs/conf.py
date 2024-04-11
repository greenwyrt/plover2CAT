# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'plover2CAT'
copyright = '2024, plants'
author = 'plants'
release = '3.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['myst_parser', "sphinx.ext.autodoc"]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'README.md']

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

autodoc_mock_imports = ["plover", "PyQt5", "dulwich", "plover_cat.plover_cat_ui", "plover_cat.affix_dialog_ui", "plover_cat.caption_dialog_ui", "plover_cat.create_dialog_ui", "plover_cat.field_dialog_ui", "plover_cat.index_dialog_ui", "plover_cat.recorder_dialog_ui", "plover_cat.shortcut_dialog_ui", "plover_cat.suggest_dialog_ui"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
# html_sidebars = { '**': ['globaltoc.html', 'relations.html', 'sourcelink.html', 'searchbox.html'] }

import os
import sys
sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath(
    os.path.join(__file__, "../../plover_cat")
))