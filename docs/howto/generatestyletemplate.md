# How to generate styles from template

Plover2CAT makes it possible to extract the styles from an `ODT` or `RTF/CRE` file. 

1. Click **Styling > Generate Style File from Template**. 
2. Select the `ODT` or `RTF/CRE` file using the file selector dialog. 
3. Plover2CAT will then extract the styles and save them in the `styles` folder as a JSON style file.

When generating styles from a tempate, only style properties specific to text are extracted and no other formatting. 

This is different from selecting an `ODT` template file to use as the style file  When an `ODT` is used directly as the template, the export of the transcript to `ODT` will use all stylistic properties, even ones not supported by Plover2CAT, and the transcript is appended to existing content in the `ODT`, such as a title page.

This is also different from `Import RTF/CRE` as the import function will load both styles and content from the file into the editor automatically.

