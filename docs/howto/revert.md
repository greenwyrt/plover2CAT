# How to revert to a previous version

Each time `Save` is clicked, a version of the transcript is saved. The different version are tracked and listed under `Previous Version` in the `History` dock, up to 100 versions in the editor, and all previous versions are available through `git`.

To return to a previous saved version, select the desired version from the dropdown, and then click `Revert`. The transcript will be reverted back (*but not the paper tape or any other files*). This will also trigger a save at the same time. 

Versioned transcripts and autosave are not the same. Autosave only saves the transcript date, not styles/page configuration, and most importantly, only provides the last autosaved transcript. Versioned transcripts contain tracked changes over time.