# How to define and insert a user field

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

To add or change a user field, go to `Insert` and then `Edit fields`. A dialog box will appear. 

### Add new user field

Fill in the "name" of the field in the `Field name` box. It is best to stick to ASCII characters. 

Then fill in the `Field value` with the desired text to show for this field. 

Then click `Add new field` in order to create a new user field. The new field name and value will appear in the table below.

### Editing a user field

Field names, shown in the first column of the column, cannot be edited. But field values can be edited by double-clicking in the cells in the second column.

To remove a field completely, use the `Remove field` button.

## Insert a user field

Defined fields are listed under `Insert > Field...` and can be inserted by clicking on the corresponding menu item. For the first 10 defined fields, they can be inserted with the shortcut `Ctrl + Shift + {0-9}`.