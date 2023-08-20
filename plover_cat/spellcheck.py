from collections import namedtuple
from itertools import product
import math
from plover.steno import Stroke, normalize_steno

# procedure from http://norvig.com/spell-correct.html, can do deletes, replaces, inserts, no transposes (because of steno order)
# extensions are reduced going along one stroke because only certain candidates in order
# but has to redo for every stroke in outline

# def edits1(word):
#     "All edits that are one edit away from `word`."
#     letters    = 'abcdefghijklmnopqrstuvwxyz'
#     splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
#     deletes    = [L + R[1:]               for L, R in splits if R]
#     # transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
#     replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
#     inserts    = [L + c + R               for L, R in splits for c in letters]
#     return set(deletes + transposes + replaces + inserts)

key_order = '''
#
S- T- K- P- W- H- R-
A- O-
*
-E -U
-F -R -P -B -L -G -T -S -D -Z
'''.split()

key_dic = {}

for ind, key in enumerate(key_order):
    key_dic[key] = ind

## likely insert key if existing key in stroke, or replacement key
neighboring_choices = {
    "#": ["T-", "P-", "H-", "*", "-F", "-P", "-L", "-T", "-D"],
    "S-": ["T-", "K-"],
    "T-": ["#", "S-", "K-", "P-"],
    "K-": ["S-", "T-", "W-"],
    "P-": ["#", "T-", "W-", "H-"],
    "W-": ["K-", "P-", "R-"],
    "H-": ["#", "P-", "R-", "*"],
    "R-": ["W-", "H-", "*"],
    "A-": ["O-"],
    "O-": ["A-"],
    "*": ["H-", "R-", "-F", "-R"],
    "-E": ["-U"],
    "-U": ["-E"],
    "-F": ["#", "*", "-R", "-P"],
    "-R": ["*", "-F", "-B"],
    "-P": ["#", "-F", "-B", "-L"],
    "-B": ["-R", "-P", "-G"],
    "-L": ["#", "-P", "-G", "-T"],
    "-G": ["-B", "-L", "-S"],
    "-T": ["#", "-S", "-D", "-Z"],
    "-S": ["-T", "-D", "-Z"],
    "-D": ["#", "-T", "-S", "-Z"],
    "-Z": ["-T", "-S", "-D"]
    }

ring_pinky_choices = ["S-", "T-", "-K", "-L", "-G", "-T", "-S", "-D", "-Z"]

# hold change in edit, key can be any of steno keys, actions can be "delete", "insert", "replaced" can be none, or key replaced 
stroke_edit = namedtuple("stroke_edit", ["key", "action", "replaced"], defaults = [None, None, None])

def edit(word):
    """word is a list of steno keys"""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [stroke_edit(R[0], "delete") for L, R in splits if R]
    possibilities = []
    for L, R in splits:
        # keys before first key, keys between split, keys after last key
        if not L:
            start = Stroke(R).first()
            if key_dic[start] != 0:
                candidates = key_order[0:key_dic[start]]
                possibilities.extend([stroke_edit(c, "insert") for c in candidates])
                possibilities.extend([stroke_edit(c, "replaced", R[0]) for c in candidates])
            end = Stroke(R).last()
            if key_dic[end] != 22:
                candidates = key_order[(key_dic[end] + 1):]
                possibilities.extend([stroke_edit(c, "insert") for c in candidates])
        elif not R:
            start = Stroke(L).first()
            if key_dic[start] != 0:
                candidates = key_order[0:key_dic[start]]
                possibilities.extend([stroke_edit(c, "insert") for c in candidates])
                possibilities.extend([stroke_edit(c, "replaced", L[0]) for c in candidates])
            end = Stroke(L).last()
            if key_dic[end] != 22:
                candidates = key_order[(key_dic[end] + 1):]
                possibilities.extend([stroke_edit(c, "insert") for c in candidates])
        else:
            pre = Stroke(L).last()
            post = Stroke(R).first()
            candidates = key_order[(key_dic[pre] + 1):key_dic[post]]
            possibilities.extend([stroke_edit(c, "insert") for c in candidates])
            possibilities.extend([stroke_edit(c, "replaced", R[0]) for c in candidates])
    possibilities.extend(deletes)
    return(set(possibilities))

def add_prob(possibilities, stroke):
    candidates = []
    # account for possibility stroke is the right now (and give it higher probability)
    candidates.append((stroke.rtfcre, stroke_edit(), 1))
    for pos in possibilities:
        if pos.action == "delete":
            # stroke with delete is correct if original had extra key
            # delete more likely if one of the neighboring keys part of stroke
            new_stroke = stroke - Stroke.from_keys([pos.key])
            alt_keys = neighboring_choices[pos.key] 
            if any([key in stroke.steno_keys for key in alt_keys]):
                prob = 0.5
            else:
                prob = 0.05
        elif pos.action == "insert":
            # stroke with insert is correct if original was missing a key
            new_stroke = stroke + Stroke.from_keys([pos.key])
            if pos.key in ring_pinky_choices:
                prob = 0.5  
            else:
                prob = 0.05
        elif pos.action == "replaced":
            # stroke with replace is correct if original had a wrong key
            # wrong key is more likely to be one of the neighboring keys of the "correct" key
            new_stroke = stroke + Stroke.from_keys([pos.key])
            new_stroke = new_stroke - Stroke.from_keys([pos.replaced])
            if pos.replaced in neighboring_choices[pos.key]:
                prob = 0.5
            else:
                prob = 0.05
        candidates.append((new_stroke.rtfcre, pos, prob))
    return(candidates)

def multi_gen_alternative(outline):
    strokes = outline.split("/")
    pos_strokes = []
    for stroke in strokes:
        pos = edit(Stroke(stroke).steno_keys)
        pos_with_prob = add_prob(pos, Stroke(stroke))
        pos_strokes.append(pos_with_prob)
    if len(pos_strokes) == 1:
        return(pos_strokes[0])
    else:
        combined_pos = product(*pos_strokes)
        combos = []
        for pos in combined_pos:
            pos = list(pos)
            outline = "/".join([i[0] for i in pos])
            edits = [i[1] for i in pos]
            total_prob = math.prod([i[2] for i in pos])
            combos.append((outline, edits, total_prob))
        return(combos)
    
def get_sorted_suggestions(outlines, engine):
    in_dict = []
    for out in outlines:
        res = engine.lookup(normalize_steno(out[0]))
        if res:
            in_dict.append((res, out[0], out[2]))
    in_dict.sort(key=lambda tup: tup[2], reverse=True)
    return(in_dict)


