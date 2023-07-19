# Docks

## Paper Tape

This dock shows the contents of the `transcript-{timestamp}.tape` file, an alternative version of the Plover Paper Tape in a QPlainTextEdit as plain text.

The paper tape is linked to the text and will scroll to the corresponding stroke when the cursor in the editor moves.

![Example of Linking](../../images/paper_text_link.gif)

Highlight a stroke in the paper tape, and click "Locate" to move to that position in the main text editor. 

## Suggestions

The Suggestions dock has a table, showing the suggestions in one column, and the outline in another column.

Plover2CAT uses the [Plover Tapey Tape plugin](https://github.com/rabbitgrowth/plover-tapey-tape) or the [Plover clippy_2 plugin](https://github.com/Josiah-tan/plover_clippy_2) for suggestions, in the default format and in the default location (`tapey-tape.txt` or `clippy_2.org`, respectively). If the plugin is not installed, or the location and format of the file is not the default, suggestions within Plover2CAT will likely not work. Plover2CAT relies on the `%s` part of the Tapey Tape output. If `%s` is part of the format, the suggestions should be extracted properly as the regex relies on the presence of the two spaces and `>` before a suggestion.

The dropdown above the table can be used to select which plugin Plover2CAT gets suggestions from.

Suggestions can be sorted by most common (default), or most recent (toggle the `By Recency` option). 

Entries will show up to the ten most common/recent entries, only if Tapey Tape has suggested an alternative outline thrice before. 

## Reveal Steno

This is a dock with a table which displays the current paragraph's text, and the underlying informating on mouse hovering. Use the `refresh` button to update the display if needed.

## Navigation

This dock shows the paragraphs that are styled as headings. Paragraphs with higher number levels are indented as needed. Double-click to move the cursor to the beginning of the heading paragraph.

## History

The History dock contains a list under `Session History` containing the actions that can be undone/redone. This history is only limited to actions performed in the present session.

Below the list is `Version History` with a dropdown list containing saved versions of the transcript.

## Audio Controls

This dock has a label `Select file to play audio` which is replaced by the file location of the file once it is selected.

From left to right, the UI elements are:
- Playback rate
- Millisecond delay between timestamp and actual audio time
- Current audio time
- Audio track 
- Total audio duration

## Toolbox

The Toolbox dock contains several tabs, of which only one can be open at any time. 

### Styling

The Styling tab contains UI controls for paragraph and text properties for the current paragraph style.

The first dropdown list shows the current style for the paragraph. Change the style for the paragraph by selecting another from the list.

To make changes to a style (which is applied to all paragraphs with this style), make changes to the following controls and then the `Modify Style` button has to be clicked to activate the change.

#### Text Properties

There is a dropdown box for font selection (based on installed system fonts). Font size can only be specified in integer format (it is not possible to supply something such as 12.5pt). 

Bold, italic, and underline buttons can be toggled. They can be used separately and in combination.

There are four different alignment buttons: left, center, right, and justified. Only one of the four buttons is able to be selected at one time.

Line spacing is measured as a % of line height. Single spacing would be 100%, and double spacing 200%.

`Average Char Width` is a read-only box. This displays the average width of a character in inches for the selected font. This is useful for setting characters per inch. However, actual characters per inch may vary if a proportional font is used (as characters will have varying width) compared to a monospace font (all characters have the same width).

#### Paragraph Properties

`First line indent` specifies how much the first line is indented compared to the rest of the paragraph.

`Tab Stop Distance` specifies the position of the tab stop if a tab appears in the text. If there is only one tab stop specified for the style, it will be editable. If there are multiple tab stops (such as when the style file is from ODF/RTF), it is not possible to edit tab stops within the editor. 

`Left Margin (Indent)` specifies the left margin of the paragraph. This is separate from the `left margin` of the page. It indents the entire paragraph relative to the `left margin` of the *page*.

`Right Margin (Indent)` is similar to the `Left Margin (Indent)`, but for the right.

`Top Margin` and `Bottom Margin` add space to the top and bottom of a paragragh, hence `(Padding)`. Microsoft Word calls this `Space before paragraph` and `space after paragraph`.

`Parent Style` is a drop down list containing all styles *except the current style*. The current style inherits formatting from the parent style, and will use those settings if nothing has been set for the current style. 

`Next Style` refers to the style to be set on the new paragraph following the current one. If a following paragraph already exists and has a style, the style will not be modified. One can for example set `Answer` as the style following `Question` and `Question` as the next style for `Answer`.

### Page Format

This tab is used for setting the page format used for export. The `page_height/page_width` and the `* Margin` fields should be self explanatory, controlling the different page margins and page dimensions. 

`Max char per line` sets the maximum characters allowed per line. 

`Max lines per page` sets the maximum number of text lines allowed per page. 

Both `max char per line` and `max lines per page` can have an `automatic value`. In this case, it is left to the editor to determine these values based on page parameters.

`Line numbering` can be checked or unchecked depending on need. The `Frequency` refers to how often a line is numbered. Setting to `5` means every fifth line is numbered.

`Line timestamp` will add a timestamp to the beginning of the line. This value is based on the earliest chronological stroke time of the line. Depending on editing, timestamps across lines may not be in order if sections of text (and steno) were moved around.

The three input fields under `Header:` are to contain any text for the header as left-aligned, center-aligned, and right-aligned text.

The three input fields under `Footer:` are to contain any text for the footer as left-aligned, center-aligned, and right-aligned text.

For both header and footer, the `%p` string is used to indicate the page number.

This page format will apply to the entire document. The values are stored in the `config.config` file, along with other project attributes. 

If an `ODT` file is used to set styling, page format parameters are overridden. 

### Find and Replace

The UI in the Find and Replace tab starts with three radio buttons for selecting the type of search, followed by a text input for the string to search for, and the `Next` and `Previous` buttons for navigating through searchs.

The next text input is to hold the string to replace the match with, and buttons for doing the relace `Once` on the selected match, or `All` for all matches in the document.

The three options that can be applied are `Match Case`, `Whole Word/Stroke` and `Wrap` may be disabled based on the kind of search selected.

### Paragraph Properties

This tab holds inputs for the common paragraph properties that are saved as second-level keys in the `transcript-{timestampe}.transcript` file, namely `creationtime`, `edittime`, `audiostarttime`, `audioendtime` and `notes`.

To discourage any accidental editing, a checkbox has to be clicked to enable editing and a button for confirming changes, and it locks when any writing is done.

### Audio recording

This tab holds the parameters that can be specified for audio recording. 

- Input Device:  Choices will be any audio inputs available to the computer such as a microphone. If the computer has a microphone, and the headphone also has mic input, these will be different choices in the menu.

- Audio Codec: Windows systems like have PCM WAV at a minimum.

- File Container: A guess on the file format for the audio will be made based on the audio codec. If the codec is not one of the common ones, the audio file will not have a file extension, and users have to manually adding a file extension after recording is done.

- Sample Rate and Channels can be left on default, and the software will pick the best fit.

- Encoding Mode

  - Constant Quality: The recording will be done based on the quality slider, varying the bitrate to keep the same quality.
  - Constant Bitrate: The recording will use the same bitrate throughout, but quality of the recording will vary.

By default, the audio recording is saved into the `audio` folder. 

### Spellcheck

This tab contains the controls needed for spellchecking.

The first dropdown list is to select a language dictionary.

The `Search` button starts off a search for any words which do not pass spellcheck. The error will show up in the `Detected:` field on the top right, and suggestions in the list area below.

`Skip` will pass over this result and continue spellchecking.

`Ignore All` will ignore this result in other parts of the document, only for the session.

`Change` will change the detected result to the highlighted choice among the suggestions.
