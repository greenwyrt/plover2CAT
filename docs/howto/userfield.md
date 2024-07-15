# Define and insert a user field

User fields are text elements that have a field name, and a text value defined by the user. All fields with the same name will show the same value, and change if the value changes.

## Defining a user field

Plover2CAT comes with default user fields available for insertion in the form of four different speakers. 

```
{
  "SPEAKER_STPHAO": "Mr. Stphao",
  "SPEAKER_SKWRAO": "Ms. Skwrao",
  "SPEAKER_EUFPLT": "Mr. Eufplt",
  "SPEAKER_EURBGS": "Ms. Eurbgs",
}
```

To add or change a user field, go to **Insert > Edit fields**. A dialog box will appear. 

### Add new user field

1. Fill in the "name" of the field in the `Field name` box. Use ASCII characters. 

2. Fill in the `Field value` with the desired text to show for this field. 

3. Click `Add new field` in order to create a new user field. The new field name and value will then appear in the table below.

### Editing and removing a user field

Field names, shown in the first column of the table, cannot be edited. Field values can be edited by double-clicking in the cells in the second column.

To remove a field completely, select the row in the table and click the `Remove field` button.

## Insert a user field

Defined fields are listed under `Insert > Field...` and can be inserted by clicking on the corresponding menu item. For the first 10 defined fields, they can be inserted with the shortcut `Alt + {0-9}`.

The dictionary outline would be `{#alt(0)}` for the first field, `{#alt(1)}` for the second and so on.