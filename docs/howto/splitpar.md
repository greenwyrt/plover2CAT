# How to split a paragraph

**Split Paragraph** is located under the **Steno Actions** menu and on the toolbar.

Click to set the cursor at the position for the desired split or click and drag to select characters. The "split" will occur at the visible cursor or the beginning of the selection after **Split Paragraph** is clicked. If the selection includes a space at the start, and the option `Before Output` for space placement in Plover, then the initial space will be removed in the new paragraph. 

A newline character sent through Plover will cause the same effect.

Note: `space_placement` is set as part of the `config.config` file when the project is first created. This option should not be changed after any steno has been input as it may mess up the underlying steno rearrangements.