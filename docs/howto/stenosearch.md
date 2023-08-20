# Use Steno Search

`Steno Search` will try to find valid steno outlines in the dictionaries based on a user-specified outline.

`Steno Search` does not refer to finding steno in the underlying transcript. See [find/replace](howto/findreplace.md) on how to do that.

## Usage

1. Activate the `Steno Search` pane in the toolbox.
2. Input the outline in the outline box.
3. Click the search button

Plover2CAT will display translations from the dictionaries with outlines similar to the one being searched. These translations are ordered in descending likelihood.

## Ordering of results

Result outlines include those that have a deletion, a replacement or an insertion of a key. For example, `EUPB` will have a search for `EUP`, `EUPG`, or `EUPBL`.

Result outlines are limited by edit distance. Outlines with multiple strokes will allow for one edit per stroke. In other words, `EUP` is one edit away from `EUPB` and will be included, but not `EU`. But for an outline such as `EUPB/TPHER`, `EUP/TPER` will be included.

Results are ordered by what kinds of edits are more common. For example, deletions of keys on the ring and pinky fingers are ranked higher than keys pressed by other fingers. Replacements/inserted are ranked higher if the key replaced/inserted is adjacent. In other words, `EUPBG` would be ranked higher than `*EUPB`.





