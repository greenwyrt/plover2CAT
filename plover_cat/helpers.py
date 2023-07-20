import pathlib
import json
import os
import time
from plover.config import Config, DictionaryConfig
from plover import log
from dulwich.porcelain import open_repo_closing

def return_commits(repo, max_entries = 100):
    with open_repo_closing(repo) as r:
        walker = r.get_walker(max_entries = max_entries, paths=None, reverse=False)
        commit_strs = []
        for entry in walker:
            time_tuple = time.gmtime(entry.commit.author_time + entry.commit.author_timezone)
            time_str = time.strftime("%a %b %d %Y %H:%M:%S", time_tuple)
            commit_info = (entry.commit.id, time_str)
            commit_strs.append(commit_info)
    return(commit_strs)

def ms_to_hours(millis):
    """Converts milliseconds to formatted hour:min:sec.milli"""
    seconds, milliseconds = divmod(millis, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return ("%02d:%02d:%02d.%03d" % (hours, minutes, seconds, milliseconds))

def in_to_pt(inch):
    inch = float(inch)
    return(inch * 72)

def pixel_to_in(pixel):
    pixel = float(pixel)
    return(pixel / 96)

def in_to_pixel(inch):
    inch = float(inch)
    return(inch * 96)

def inch_to_spaces(inch, chars_per_in = 10):
    if isinstance(inch, str):
        inch = float(inch.replace("in", ""))
    return round((inch * chars_per_in))

def save_json(json_dict, file_path):
    """Save dict to json file"""
    file_path = pathlib.Path(file_path)
    if not file_path.parent.exists():
        file_path.parent.mkdir()
    if not file_path.exists():
        file_path.touch()        
    with open(file_path, "r+") as f:
        json.dump(json_dict, f, indent = 4)
        log.debug(f"Data saved in {str(file_path)}.")

def add_custom_dicts(custom_dict_paths, dictionaries):
    """Takes list of dictionary paths, returns Plover dict config"""
    dictionaries = dictionaries[:]
    custom_dicts = [DictionaryConfig(path, True) for path in custom_dict_paths]
    return custom_dicts + dictionaries
    
## copied from plover_dict_commands
def load_dictionary_stack_from_backup(path):
    """Restore Plover dicts from backup file."""
    try:
        with open(path, 'r') as f:
            try:
                dictionaries = json.load(f)
            except json.JSONDecodeError:
                dictionaries = None
        if dictionaries:
            old_dictionaries = [DictionaryConfig.from_dict(x) for x in dictionaries]
            os.remove(path) #backup recovered, delete file
            return old_dictionaries
        else:
            return None
    except IOError:
        return None

def backup_dictionary_stack(dictionaries, path):
    """Takes Plover dict config, creates backup file."""
    log.debug("Backing up Plover dictionaries to %s", path)
    if dictionaries:
        with open(path, 'w') as f:
            json.dump([DictionaryConfig.to_dict(d) for d in dictionaries], f)
    else:
        try:
            os.remove(path)
        except OSError:
            pass

def remove_empty_from_dict(d):
    if type(d) is dict:
        return dict((k, remove_empty_from_dict(v)) for k, v in d.items() if v and remove_empty_from_dict(v))
    elif type(d) is list:
        return [remove_empty_from_dict(v) for v in d if v and remove_empty_from_dict(v)]
    else:
        return d

def hide_file(filename):
    import ctypes
    FILE_ATTRIBUTE_HIDDEN = 0x02
    ret = ctypes.windll.kernel32.SetFileAttributesW(filename, FILE_ATTRIBUTE_HIDDEN)    
    if not ret: # There was an error.
        raise ctypes.WinError()    
