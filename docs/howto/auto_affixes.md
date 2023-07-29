# Add automatic paragraph affixes

Plover2CAT provides the ability to add defined text strings to the beginning and end of every paragraph based on the style of the paragraph.

This can be very useful in certain cases, such as a Question style where every paragraph may begin with `Q.` and end with a `?`

## Enable automatic paragraph affixes

To enable automatic affixes, click **Styling > Automatic Paragraph Affixes**. 

Then set affixes if none are defined.

## Set affixes

To open the affix editor, go to **Styling > Edit Paragraph Affixes**.

1. Select the desired style to set affixes to from the dropdown list. Existing values for the style are shown in the Prefix string and Suffix string fields, else the fields are blank. 

2. Fill out the Prefix string and Suffix string fields. Leave empty if not needed.

3. Click `Save` to save the affixes for the style. 

4. Then click `OK` to return to the main editor. If `Cancel` is pressed, the changes are discarded.

## Tab insertions

Affixes can contain tab characters but not new lines. To insert a tab into a prefix/suffix field, place the cursor at the desired position. Then click `Insert tab at cursor`.

## Usage

When enabled, the suffix string for the style will be applied to the end of the paragraph after the user creates a new paragraph under the present one. In other words, enabling this feature does not apply suffixes to pre-existing paragraphs.

The prefix string is only added to non-empty paragraphs and will only appear at paragraph start after text is inserted. 

Similar to the suffix, prefixes will not be added to pre-existing paragraphs.



