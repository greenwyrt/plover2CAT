# Syncing with media

## Set up a time offset for syncing with writing

Plover2CAT will keep track of the media time in addition to the real time of a stroke when a media file is being played. Both times will show up in the paper tape.

To add an offset to the recorded time, change the time offset located in the Media Controls dock. By default, the offset is `0ms`. This value can be changed using the arrow buttons in the box. When an offset is set, the recorded media time will be set off by the millisecond value. A positive offset value means the recorded time is x milliseconds behind than the real time, while a negative offset means the recorded time is x milliseconds ahead of the real time.

## Seeking to cursor position

With **Media > Sync Media Position**, Plover2CAT will move the media track to the closest available time from the location of the text cursor. 

If the media is playing when this is used, the media will start playing from the new position. For paused or stopped media, the media will not automatically play.

Plover2CAT will jump to a time offset. This is controlled by the time offset in the Media Controls dock. When an offset is positive, Plover2CAT will move an additional x milliseconds from the media time. If an offset is negative, Plover2CAT will move a additional x milliseconds ahead of the media time. 