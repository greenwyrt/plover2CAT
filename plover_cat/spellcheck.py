from collections import namedtuple
from plover.steno import Stroke
# # b relative to a, wrong outline relative to correct outline
# a = "A/SROEUD"

# b = "A/SROED"

# s = SequenceMatcher(None, a, b)

# for tag, i1, i2, j1, j2 in s.get_opcodes():
#     print('{:7}   a[{}:{}] --> b[{}:{}] {!r:>8} --> {!r}'.format(
#         tag, i1, i2, j1, j2, a[i1:i2], b[j1:j2]))
# candidate model from http://norvig.com/spell-correct.html, can do deletes, replaces, inserts, no transposes (because of steno order)
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

# # pretend word is stroke
# word = ["S-", "T-", "A-", "O-", "*"]
# splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
# deletes = [L + R[1:] for L, R in splits if R]
# # getting keys not in stroke
# not_in = word.__invert__()
# not_in_keys = not_in.steno_keys


# hold change in edit, key can be any of steno keys, actions can be "delete", "add", "replaced" can be none, or key replaced 
stroke_edit = namedtuple("stroke_edit", ["key", "action", "replaced"], defaults = [None])

def edit(word):
    """word is a list of steno keys"""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    possibilities = []
    for L, R in splits:
        # keys before first key, keys between split, keys after last key
        if not L:
            start = Stroke(R).first()
            if key_dic[start] != 0:
                candidates = key_order[0:key_dic[start]]
                possibilities.extend([[c] + R for c in candidates])
                possibilities.extend([[c] + R[1:] for c in candidates])
            end = Stroke(R).last()
            if key_dic[end] != 22:
                candidates = key_order[(key_dic[end] + 1):]
                possibilities.extend([R + [c] for c in candidates])
        elif not R:
            start = Stroke(L).first()
            if key_dic[start] != 0:
                candidates = key_order[0:key_dic[start]]
                possibilities.extend([[c] + L for c in candidates])
                possibilities.extend([[c] + L[1:] for c in candidates])
            end = Stroke(L).last()
            if key_dic[end] != 22:
                candidates = key_order[(key_dic[end] + 1):]
                possibilities.extend([L + [c] for c in candidates])
        else:
            # start = Stroke(L).first()
            # if key_dic[start] != 0:
            #     candidates = key_order[0:key_dic[start]]
            #     possibilities.extend([[c] + L + R for c in candidates])
            pre = Stroke(L).last()
            post = Stroke(R).first()
            candidates = key_order[(key_dic[pre] + 1):key_dic[post]]
            possibilities.extend([L + [c] + R for c in candidates])
            possibilities.extend([L + [c] + R[1:] for c in candidates])
            # end = Stroke(R).last()
            # if key_dic[end] != 22:
            #     candidates = key_order[(key_dic[end] + 1):]
            #     possibilities.extend([L + R + [c] for c in candidates])
    possibilities.extend(deletes)
    outlines = []
    for c in possibilities:
        outline = Stroke.from_keys(c)
        outlines.append(outline.rtfcre)
    return(set(outlines))


