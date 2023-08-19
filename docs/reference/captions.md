# Captions

`captionWorker` runs on a separate thread to accept input, format captions, and send captions to display and also other endpoints.

There are two important queues, a `word_queue` and a `cap_queue`.

Captions has a display/UI component in the main editor that accepts signals from the `captionWorker` with the caption to display.

## Input

`display_captions` is called every time there is a stroke, and will send any "new text" into the `captionWorker.intake` while keeping track of positions of text already in the caption.

The text is broken down into "words" and "spaces" and fed into `word_queue`, then `make_caps` is called.

## Formatting captions

`make_caps` formats everything in the `word_queue` based on parameters. Formatted caps are sent into the `cap_queue`

## Time-controlled display

There is a `QTimer` that triggers for sending a caption to display and an endpoint if specified. No matter how fast text is intaken or captions are formatted and added to queue, captions are only "released" when the timer goes off at the specified interval.

`send_cap` will always send to display, and only one of the endpoints, one of `send_*`



