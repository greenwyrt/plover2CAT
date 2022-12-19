def remove_strings(stroke_data, backspace):
    """Mimics backspaces on stroke data

    Arg:
        stroke_data (list): list of steno stroke elements in
            [time, steno_strokes, translation, ...] format
        backspace (int): number of backspaces
        
    Returns:
        List of steno strokes, with # of backspaces removed from end 

    """
    stroke_data = stroke_data[:]
    if len(stroke_data) > 0:
        if not all(isinstance(el, list) for el in stroke_data):
            stroke_data = [stroke_data]
    backspace = backspace
    if len(stroke_data) == 1:
        stroke = stroke_data[0]
        if backspace >= len(stroke[2]):
            return []
        else:
            string = stroke[2]
            string = string[:-backspace]
            stroke[2] = string
            return [stroke]     
    for stroke in reversed(stroke_data[:]):
        stroke = stroke[:]
        stroke_data.remove(stroke)
        if backspace >= len(stroke[2]):
            backspace = backspace - len(stroke[2])
            # backspace == 0 should be almost all cases (* removes one-stroke word and space before/after)
            if backspace == 0: break
        else:
            string = stroke[2]
            string = string[:-backspace]
            stroke[2] = string
            stroke_data.append(stroke)
            break
    return stroke_data

def split_stroke_data(stroke_data, start):
    """Returns tuple of lists of steno strokes, split at position start.

    Args:
        stroke_data (list): list of steno stroke elements in 
            [time, steno_strokes, translation, ...] format
        start (int): position for splitting, based on text lengths in 
            the translation element of stroke

    Returns:
        tuple of two lists of steno strokes, split at the position 
            specified by the start argument based on the translation lengths. 

    """
    # hack here if stroke data only has one stroke, so not list of list
    if len(stroke_data) > 0:
        if not all(isinstance(el, list) for el in stroke_data):
            stroke_data = [stroke_data]
    split = False
    first_part = []
    second_part = []
    if start == 0:
        return [], stroke_data
    for stroke in stroke_data:
        start = start - len(stroke[2])
        if start > 0:
            first_part.append(stroke)
        elif start == 0:
            # special case but likely most common when split occurs at boundary of stroke
            first_part.append(stroke)
            split = True
        else:
            if split:
                second_part.append(stroke)
            else:
                text = stroke[2]
                # arbitrarily, the stroke data goes with first part if middle of split
                # the second part will still have the time
                first_part.append([stroke[0], stroke[1], text[:start]])
                second_part.append([stroke[0], "", text[start:]])
                split = True
    if len(first_part) > 0:
        if not all(isinstance(el, list) for el in first_part):
            first_part = [first_part]
    if len(second_part) > 0:
        if not all(isinstance(el, list) for el in second_part):
            second_part = [second_part]
    return first_part, second_part

def extract_stroke_data(stroke_data, start, end, copy = False):
    """Returns piece(s) of stroke data mimicking a cut

    Args:
        stroke_data (list): list of steno stroke elements in 
            [time, steno_strokes, translation, ...] format
        start (int): start of split
        end (int): end of split
        copy (boolean): whether to return part between start and end,
            or combined leftovers
    
    Returns:
        Depends on state of copy. If True, a list of stroke data,
            extracted from the stroke_data between positions start 
            and end. If False, tuple of stroke data list, 1) from 
            beginning to start position + from end position 
            to last element in stroke_data, and 2) extracted from 
            the stroke_data between positions start and end

    """
    before, keep = split_stroke_data(stroke_data, start)
    selected, after = split_stroke_data(keep, end - start)
    if after and not before:
        left_over = after
    elif before and not after:
        left_over = before
    else:
        left_over = before + after
    if copy:
        # only return copied part
        return selected
    else:
        # need to return selected part, but original block needs to be reset 
        return left_over, selected
            
def stroke_at_pos(stroke_data, pos):
    if len(stroke_data) > 0:
        if not all(isinstance(el, list) for el in stroke_data):
            stroke_data = [stroke_data]
    for i, stroke in enumerate(stroke_data):
        pos = pos - len(stroke[2])
        if pos <= 0:
            return(stroke)       

def stroke_pos_at_pos(stroke_data, pos):
    if len(stroke_data) > 0:
        if not all(isinstance(el, list) for el in stroke_data):
            stroke_data = [stroke_data]
    cumlen = 0
    for i, stroke in enumerate(stroke_data):
        pos = pos - len(stroke[2])
        # print(pos)
        if pos <= 0:
            return(cumlen, cumlen + len(stroke[2]))
        cumlen =  cumlen + len(stroke[2])
    return((0, 0))
