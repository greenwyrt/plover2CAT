# Code Documentation

This section contains the *code documentation* for plover2CAT. For descriptions of the editor and its functions, use the Reference section.

Parts of the documentation, especially involving the dialogs, should be read together with the relevant sections in How To and Reference which describe user interactions and the different GUI elements.

The GUI is built using the Qt Framework as a plugin to Plover. The primary interfact is contained in a `QMainWindow` with multiple docks and possible dialogs. 

Text is shown in a `QTextEdit` which holds all the data such as outlines and times. The custom objects stored in each `QTextBlock`'s `userData` are described in [Custom Elements](elements.md).

As Qt uses camelCase and Python best practice is snake_case, the codebase keeps camelCase for GUI elements such as in UI files while using snake_case elsewhere.



```{toctree}
:maxdepth: 1
Custom Elements <elements.md>
Editor Dialogs <dialog.md>
helpers
commands
workers
transcripteditor
editor
```

To document:

Editor
