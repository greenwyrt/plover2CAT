# Add automatic paragraph affixes

Plover2CAT provides the ability to add defined text strings to the beginning and end of every paragraph based on the style of the paragraph.

This can be very useful in certain cases, such as a Question style where every paragraph may begin with `Q.` and end with a `?`
## Enable automatic paragraph affixes

To enable automatic affixes, go to the `Styling` menu and then click `Automatic Paragraph Affixes`. Then set affixes if none are defined.

## Set affixes

To open the affix editor, go to `Styling` and then `Edit Paragraph Affixes`. 

First select the desired style to set affixes to. Existing values for the style will be shown in the Prefix string and Suffix string fields, else the fields will be blank. Fill out the fields as needed.

Click `Save` to save the affixes for the style. Then click `OK` to return to the main editor. If `Cancel` is pressed, the changes are discarded.

## Tab insertions

Affixes can contain tab characters but not new lines. To insert a tab into a prefix/suffix field, first place the cursor at the desired position. Then click `Insert tab at cursor`.

## Usage

When enabled, the suffix string for the style will be applied to the end of the paragraph after the user creates a new paragraph under the present one. In other words, enabling this feature does not apply suffixes to pre-existing paragraphs.

The prefix string is only added to non-empty paragraphs and will only appear at paragraph start after text is inserted. 

Similar to the suffix, prefixes will not be added to pre-existing paragraphs.



