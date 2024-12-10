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

## Document Worker

`documentWorker` is used to export the transcript in a separate thread. Each file format is called through `save_x`.

During the export, as each paragraph is processed, a `progress` signal is emitted with the paragraph number. This is used for progress bars for long exports. After completing export, the `finished` signal is sent. 

Any new `save_x` format needs to include code for emitting those two signals.

```{eval-rst}
.. automodule:: documentWorker
    :members:
    :show-inheritance:
    :member-order: bysource
```
