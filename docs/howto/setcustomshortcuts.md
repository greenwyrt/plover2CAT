# Set custom shortcuts for menu items

Plover2CAT provides keyboard shortcuts for some of the common actions by default. However, shortcuts can be set for all menu items by using a JSON file with action identifiers and shortcut keysequences.

First, go to Plover and click `Open Config Folder` under `File`. This will open the Plover configuration file.

In this folder, create a new folder called `plover2cat`. Then create a new JSON file called `shortcuts.json`.

Within this JSON file should be the `Action Identifier` and `keysequence` pairs. The `Action Identifier` for each menu item is listed in the [menu reference page](../reference/menu.md). 

An example JSON is presented here.

```
{
    "actionClose": "Ctrl+Alt+C", # set the shortcut Ctrl+Alt+C to menu item "Close"
    "actionSave": "" # override the default Ctrl+S shortcut for menu item "Save"
}
```

A shortcut is composed of 0 or more modifiers (`Ctrl`, `Shift`, `Alt`, `Meta`) and a key (ie `C`, `Enter` and so on), separated by a `+`.

Note that changes only take effect when Plover2CAT is restarted.

Note that `Ctrl + {0-9}` and `Ctrl + Shift + {0-9}` are sets of key combinations reserved for switcing between paragraph styles and inserting field elements, respectively. It is best not to use these combinations for other shortcuts.


