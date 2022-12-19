# How to select a style file

Plover2CAT can read in JSON and ODT (Open Document Format text document) files and extract style information out of them.

When a transcript is created, there is a default set of styles. To use a different set of styles, use `Select Style File` under the `Styling` menu. A file dialog will appear for selecting either a `JSON` or `ODT` file to be loaded. The style file will also be copied to the `style` folder in the transcript folder.

Note that when a new style file is loaded, the new styles overwrites the existing styles. So any existing paragraphs in the editor with the old style names may not have any styling information after a new set of styles is loaded if names do not match. For this reason, it is better to create and modify styles if there is existing transcript text, or load the style file right after creating a new transcript.