# Editor Dialogs

This section documents the code underlying the different editor dialogs. Read this together with the reference dialog descriptions.

Plover2CAT dialogs have their own UI and code files as they subclass `QDialog`. In general, these dialogs will receive a dict along with other parameters, and changes are made to the internal dict. After `accepted`, the dialog dict is then accessed from outside.

```{eval-rst}
.. automodule:: affixDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

```{eval-rst}
.. automodule:: fieldDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

```{eval-rst}
.. automodule:: shortcutDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

```{eval-rst}
.. automodule:: indexDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

```{eval-rst}
.. automodule:: captionDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

```{eval-rst}
.. automodule:: suggestDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

```{eval-rst}
.. automodule:: recorderDialogWindow
    :members:
    :show-inheritance:
    :member-order: bysource
```

