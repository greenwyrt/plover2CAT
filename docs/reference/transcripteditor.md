# Transcript Editor

Each transcript is encapsulated in its own `PloverCATEditor` class, which subclasses `QTextEdit`.

## Attributes

potential remove:
- `styles_path`: path referencing style file

- `config`: dict holding transcript configuration
- `engine`: reference to Plover engine
- `file_name`: path for transcript folder
- `repo`: Dulwich repo
- `backup_document`: dict key:value, paragraph number: block data
- `tape`: paper tape text as a long string with `\n` line separators
- `dictionaries`: list of transcript-specific dictionaries 
- `styles`: dict holding styles
- `txt_formats`: dict holding "full" font formatting info (after recursion)
- `par_formats`: dict holding "full" paragraph formatting info (after recursion)
- `user_field_dict`: dict, holds user defined fields 
- `auto_paragraph_affixes`: dict, holds affixes for styles
- `audio_file`: path referencing file being played/recorded
- `cursor_block`: integer, blockNumber of QTextCursor at last stroke
- `cursor_block_position`: integer, position of QTextCursor within block at last stroke
- `stroke_time`: text string timestamp of last stroke
 `last_raw_steno`: string, raw steno of last stroke
- `last_string_sent`: string, text sent with last stroke
- `last_backspaces_sent`: integer, number of backspaces sent with last stroke
- `undo_stack`: holds `QUndoStack`
- `spell_ignore`: list of words to ignore in spellcheck, temporary for session
- `_completer`: holds the autocompleter
- `player`: holds a QMediaPlayer instance
- `recorder`: holds a QAudioRecorder instance


## Methods


### Transcript management
- `load`: takes a path, loads the transcript, and all related data
- `load_transcript`:  loads transcript data into editor and `userData` in blocks
- `load_tape`: load tape data
- `save`: saves transcript
- `save_transcript`: extracts transcript data from editor, only updates values if necessary, ie every par starting with first with `userState` == 1
- `close_transcript`: clean up transcript for closing
- `dulwich_save`: commits transcript files to repo with commit message
- `get_dulwich_commits`: return list of commit times and id
- `revert_transcript`: revert transcript based on commit id
- `autosave`: saves transcript to hidden file

### Config management
- `load_config_file`: loads config from file path, creates default if path does not exist
- `save_config_file`: saves config in JSON file
- `get_config_value`: get config value by `key`
- `set_config_value`: set config value by `key`, saves
- `load_spellcheck_dicts`: return list of paths for transcript spellcheck dicts

### Dict management
- `load_dicts`: load transcript dictionaries to Plover engine, make backup of original dictionary stack
- `restore_dictionary_from_backup`: restore original dictionary stack from backup

### Style management
- `load_check_styles`: loads style file based on path, copies to `style/`, or creates default `style.json` in `styles/` if path does not exist
- `gen_style_formats`: generates recursive `QTextFormat` objects for styles
- `set_style_property`: set top level, `paragraphproperties` or `textproperties` attributes
- `get_style_property`: get style properties by name and attribute

### Steno management

- `on_stroke`: big function that manages insertion/deletion of data and text based on plover hook
- `log_to_tape`: create tape string, append to file, and send string to update tape GUI
- `update_block_times`: updates block with edit time and audio time, create `BlockUserData` if needed and set `creationtime`
- `split_paragraph`: creates new paragraph
- `merge_paragraphs`: combines two adjacent paragraphs
- `cut_steno`: cut/copies steno and stores (depending on arguments), returns steno for cut/copy storage if specified

### Audio management

- `get_audio_time`: returns audio time of media with delay correction

- `navigate_to`: function accepts block number, moves and sets editor cursor to beginning of block

## Signals

`send_message`: string to show in main window status bar
`send_tape`: string to append to tape dock

