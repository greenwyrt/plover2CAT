# Set custom shortcuts for menu items

Plover2CAT provides keyboard shortcuts for some of the common actions by default. However, shortcuts can be set for all menu items 


Go to `Help` and then `Edit Menu Shortcuts`. Select the desired menu item in the dropdown list. Then enter the desired shortcut, pressing `Validate and save` to check if this shortcut can be set.

Note that `Ctrl + {0-9}` and `Ctrl + Shift + {0-9}` are sets of key combinations reserved for switching between paragraph styles and inserting field elements, respectively. It is best not to use these combinations for other shortcuts.

Additionally, menu items cannot share shortcuts, so each shortcut must be unique.

Press `OK` to set shortcuts and save the set shortcuts to the shortcut file.


## Setting shortcuts with shortcut file

The alternative way to set shortcuts is by using a JSON file with action identifiers and shortcut keysequences.

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

Note that `Ctrl + {0-9}` and `Ctrl + Shift + {0-9}` are sets of key combinations reserved for switching between paragraph styles and inserting field elements, respectively. It is best not to use these combinations for other shortcuts.


