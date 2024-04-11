# Workers

The `*Worker` classes are used when offloading work to a separate thread. They all subclass `QObject`, and are moved to a `QThread` instance by `moveToThread`.


## `captionWorker` details

`captionWorker` runs on a separate thread to accept input, format captions, and send captions to display and also other endpoints.

There are two important queues, a `word_queue` and a `cap_queue`.

Captions has a display/UI component in the main editor that accepts signals from the `captionWorker` with the caption to display.

`display_captions` is called every time there is a stroke, and will send any "new text" into the `captionWorker.intake` while keeping track of positions of text already in the caption.

The text is broken down into "words" and "spaces" and fed into `word_queue`, then `make_caps` is called.

`make_caps` formats everything in the `word_queue` based on parameters. Formatted caps are sent into the `cap_queue`.

```{eval-rst}
.. automodule:: captionWorker
    :members:
    :show-inheritance:
    :member-order: bysource
```



```{eval-rst}
.. automodule:: documentWorker
    :members:
    :show-inheritance:
    :member-order: bysource
```
