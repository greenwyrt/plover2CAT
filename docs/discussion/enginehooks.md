# Plover engine hooks

Of the three engine hooks with data for `strokes`, `stroked`, `send_string` and `send_backspace`, the two `send_*` hooks will trigger before `stroked`. Therefore, `stroked` is used as the trigger to update the `strokes` data, as by then the number of backspaces and text string Plover emits for the stroke are available. If done the other way around, `send_string` will not know the present stroke, and the code becomes more complicated with the `strokes` data always a step behind.

The `on_stroked` function in the code is the workhorse of the entire editor. It sets properties of the paragraph and modifies them before inserting the text Plover outputs, and also deleting text based on the number of backspaces Plover outputs.







