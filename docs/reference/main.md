# Main Editor Class

The main class in Plover2CAT is PloverCATWindow that subclasses `QMainWindow` and the `Ui_PloverCAT`. 

## Attributes

- `engine`: holds Plover's `engine` instance
- `player`: instance of `QMediaPlayer`
- `recorder`: instance of `QAudioRecorder`
- `config`: dict holding transcript configuration
- `file_name`: path for transcript folder
- `styles`: dict holding styles
- `txt_formats`: dict holding "full" font formatting info (after recursion)
- `par_formats`: dict holding "full" paragraph formatting info (after recursion)
- `speakers`: (not utilized yet) dict to hold speaker ids
- `styles_path`: path referencing style file
- `stroke_time`: text string timestamp of last stroke
- `audio_file`: path referencing file being played/recorded
- `cursor_block`: integer, blockNumber of QTextCursor
- `cursor_block_position`: integer, position of QTextCursor within block
- `last_raw_steno`: string, raw steno of last stroke
- `last_string_sent`: string, text sent with last stroke
- `last_backspaces_sent`: integer, number of backspaces sent with last stroke
- `undo_stack`: holds `QUndoStack`
- `cutcopy_storage`: `element_collection` holding steno to paste
- `spell_ignore`: list of words to ignore in spellcheck, temporary for session
- `repo`: Dulwich repo
- `numbers`: dict holding corresponding Plover numbers

## Initialized

Actions upon initialization performed in this order

- UI is initialized first
- Detected audio inputs are added to `audio_device` selection
- Detected audio codecs are added to `audio_codec` selection
- Supported audio containers added to `audio_container` selection
- Supported audio sampling rate added to `audio_sample_rate` selection
- Standard channel and bitrate selections are added to `audio_channels` and `audio_bitrate`
- History and Paper docks are tabbed together
- Steno data and Audio docks are tabbed together
- Windows settings (size/location, dock positions, fonts) are restored 
- Default menu items are disabled on start
- Menu shortcuts are changed based on user config
- Load US spellcheck dictionary


## Methods

The methods are roughly grouped into a few different kinds: GUI-directed, transcript/dict/style management, steno editing, audio management, import/export formatting.

Methods that use manipulate the stroke data or use `QUndoCommands` are in *italics*.

### GUI

- `set_shortcuts`: reads `shortcuts.json` and makes menu shortcuts as needed
- `about`: displays version
- `acknowledge`: displays acknowledgments 
- `open_help`: sends user to help docs
- `context_menu`: opens right-click menu
- `menu_enabling`: enable/disables menu choices when transcript is open
- `model_from_file`: reads completion choices from `wordlist.json`
- `setup_completion`: sets up autocomplete using `wordlist.json` into editor if menu option toggled
- `change_window_font`: change font family/size for window
- `change_backgrounds`: changes background color for window
- `change_tape_font`: change font family/size for tape dock
-  `show_invisible_char`: show all characters in editor pane
- `calculate_space_width`: calculates average chars per inch for selected font
- `jump_par`: move cursor to selected paragraph
- `show_find_replace`: brings Find/Replace pane to front, if selection exists, place in search field

### Transcript management

- `create_new`: creates new transcript project
- *`open_file`*: opens existing transcript project
- `save_file`: saves transcript files
- `dulwich_save`: commits transcript files to repo with commit message
- *`load_transcript`*: loads transcript data into editor and `userData` in blocks
- `revert_file`: reverts transcript back to selected commit from repo
- *`save_as_file`*: saves transcript data and tape into new location
- `close_file`: closes transcript project and cleans up editor
- `action_close`: quits editor window
- `open_root`: opens transcript dir through system explorer

### Dictionary management

- `create_default_dict`: creates default dict in `dict/` subdir
- `add_dict`: file selection dialog for custom dict to add to `dict/` and plover dictionary stack
- `remove_dict`: file selection dialog to remove custom dict from `dict/` and plover dictionary stack
- `set_dictionary_config`: takes list of dictionary paths, generate default dict if missing, backups present dictionary stack and loads transcript dictionaries
- `restore_dictionary_from_backup`: restore plover dictionary stack from backup file

### Config management

- `load_config_file`: reads config file and sets editor UI variables
- `save_config`: reads `self.config` dict and saves it to file
- `update_config`: retrieves config values from editor UI variables and saves it to file

### Style management

- `setup_page`: reads `config` and set page dimensions
- `create_default_styles`: creates default `style.json` in `styles/`
- `load_check_styles`: loads style file based on path, copies to `style/`
- `gen_style_formats`: generates complete font and paragraph format dicts recursively for each style
- `select_style_file`: load style fil from user file selction
- `style_from_template`: reads ODF or RTF file, extracting only style information to write to new style file
- `display_block_data`: triggered manually after text changes or split/merge, updates style and block properties display, triggers autocomplete dropdown if toggled
- `display_block_steno`: takes strokes, update Reveal Steno dock with strokes, called from `display_block_data`
- *`update_paragraph_style`*: updates style of present paragraph block
- `update_style_display`: updates UI elements to display present style
- `style_edit`: changes properties of current style to user selections
- `new_style`: create a new style based on current style
- *`refresh_editor_styles`*: complete refresh of all paragraph blocks based on present styles
- *`to_next_styles`*: sets current block style based on `nextstylename` attribute of previous block if exists
- *`change_style`*: applies new user-selected style to paragraph
- `editor_lock`: toggle to lock/unlock paragraph properties for editing
- `edit_user_data`: update `userData` of block after user edits in UI

### Steno editing

- `on_send_string`: hooked to Plover `send_string`, stores sent string
- `count_backspaces`: hooked to Plover `send_backspaces`, stores number of backspaces sent
- `log_to_tape`: hooked to Plover `stroked`, updates paper tape with most recent stroke along with timestamps and cursor position
- `get_tapey_tape`: summarizes suggestions from Tapey Tape plugin if available
- `stroke_to_text_move`: move to corresponding position in editor based on cursor position in tape dock
- `text_to_stroke_move`: move to corresponding stroke in tape based on steno data under editor cursor
- *`tape_translate`*: extract stroke data from selected tape file, translates and overwrite current transcript
- *`on_stroke`*: hooked to Plover `stroked`, main function, performs multiple functions relating to updating block data, managing steno data, inserting/removing text/new lines as needed 
- *`split_paragraph`*: creates new paragraph
- *`merge_paragraphs`*: combines two adjacent paragraphs
- *`copy_steno`*: extracts text and steno from selection
- *`cut_steno`*: cuts text and steno from selection
- *`paste_steno`*: inserts previously stored steno and text into cursor location
- `reset_paragraph`: removes text and all data from block
- *`define_retroactive`*: takes steno and text from selection, asks for new translation, then replaces all occurrences in transcript
-  `define_scan`: searches for last untranslated and triggers `define_retroactive`
- *`add_autocomplete_item`*: adds selection to `wordlist.json` for autocompletion
- *`insert_autocomplete`*: autocompletion after selection from dropdown, replaces partial word with full selection
- *`insert_text`*: user dialog to insert pure text, adds blank in steno data
- `mock_del`: triggered on `Del` keypress, replicates normal `Del` behaviour
- `search`: wrapper function for three types of searches
- `text_search`: search editor text using `QTextEdit` search functions
- `steno_wrapped_search`: wrapper for both directions of `steno_search`
- *`steno_search`*: searches the `userData` stroke data for matches
- `untrans_search`: regex search of text for untranslated steno
- `search_text_options`: if text search selected, enables/disables allowed search options
- `search_steno_options`: if steno search selected, enables/disables allowed search options
- `search_untrans_options`: if untrans search selected, enables/disables allowed search options
- *`replace`*: replaces match result from search with field text, moves to next match
- `replace_everything`: iteratively replaces all matches with field text
- `sp_check`: checks word in dictionary
- `spellcheck`: spellchecks transcript word by word, stop and display suggestions
- `sp_ignore_all`: add word to be ignored by spellcheck
- *`sp_insert_suggest`*: change selection to suggestion
- `set_sp_dict`: load selected spellcheck dictionary
- `insert_image`: inserts selected image at cursor position


### Audio management

- `open_audio`: select an existing audio file
- `set_up_video`: create video widget if video available
- `show_hide_video`: show/hide video frame
- `play_pause`: play/pause media, adds timestamp to paragraph
- `stop_play`: stops media, adds timestamp to paragraph
- `update_duration`: updates audio UI slider and time
- `update_seeker_track`: sets audio track slider position and current time
- `set_position`: changes audio position based on user input
- `seek_position`: skips forward/backwards 5000ms on audio track
- `update_playback_rate`: changes audio playback rate
- `record_controls_enable`: disables recording controls when actively recording
- `recorder_error`: returns recorder error in status bar
- `record_or_pause`: manages start/pause of recording
- `stop_record`: stop recording
- `update_record_time`: updates states bar with recording duration


### Import/Export

- `export_text`: export plain text
- *`export_ascii`*: exports ASCII format
- *`export_html`*: exports HTML format
- *`export_plain_ascii`*: exports plain ASCII
- *`export_srt`*: exports to SRT
- *`export_rtf`*: exports RTF
- `import_rtf`: imports RTF
