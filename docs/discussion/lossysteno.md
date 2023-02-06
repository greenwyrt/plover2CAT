# Lossy `steno` data

Each time a stroke is written, Plover2CAT will first parse the the number of backspaces and/or text string the Plover engine outputs. The text string element (third) in the `strokes` array will be modified. The resulting `strokes` list will contain a *lossy* representation of the steno and the text as the backspaces Plover emits are used, but not recorded explicitly. 

Take for example writing `pleasing`.

```
strokes = [
["2001-01-01T01:23:45.678", "PHRES", "please"]
]
```

When `-G` is stroke, for the suffix `-ing`, Plover will emit one backspace (to remove the `e`), and the text string `ing`. The stroke representation will become:

```
strokes = [
["2001-01-01T01:23:45.678", "PHRES", "pleas"],
["2001-01-01T01:24:56.789", "-G", "ing"]
]
```
One benefit of doing this is that the user can still search the steno for the stroke `PHRES` and find `pleasing`. 

If a `*` is stroked, it will erase the complete stroke. Imaging having written `-T KAT S-` for `The at is`.

```
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"],
["2001-01-01T01:23:46.789", "S-", " is"]
]
```

If `*` is used, Plover will emit *three* backspaces (two spaces for `is` and one for the space at the front). Then `strokes` is updated back to: 

```
strokes = [
["2001-01-01T01:23:45.678", "-T", "The"],
["2001-01-01T01:23:46.789", "KAT", " cat"]
]
```

The tape will still record `-T KAT S- *` but the stroke data only has `-T KAT`

Advantages for this method is that it keeps the transcript file size small without multiple strokes of `["timestamp", "*", ""]` cluttering the file. This works well with Plover theory where the `*` is used on its own as `undo`. In other theories where `*` may be used on its own as part of an outline, then `*` will be missing from the transcript data.