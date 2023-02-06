# How to select a style file

Plover2CAT can read in JSON and ODT (Open Document Format text document) files to use as style templates.

When a transcript is created, there is a default set of styles. To use a different set of styles, use `Select Style File` under the `Styling` menu. A file dialog will appear for selecting either a `JSON` or `ODT` file to be loaded. The style file will also be copied to the `style` folder in the transcript folder.

Note that when a new style file is loaded, the new styles overwrites the existing styles. So any existing paragraphs in the editor with the old style names may not have any styling information after a new set of styles is loaded if names do not match. For this reason, it is better to create and modify styles if there is existing transcript text, or load the style file right after creating a new transcript.

The selected style file is then used for export. When an `ODF` file is selected as the style file, and Plover2CAT is exporting the transcript to `ODF`, all style properties, even those that Plover2CAT does not support will be present in the transcript `ODF` file, and the transcript contents are appended to any text present in the style `ODF`.