# How to add extra language dictionaries

Spellcheck in the editor is powered by the [`spylls`](https://github.com/zverok/spylls) package. `Spylls` comes with the `en-US` dictionary from Hunspell for spellchecking. To use a different language dictionary, such as `en-GB`, download the desired dictionary extension from LibreOffice. LibreOffice packages all English dictionaries together as one `oxt` zip file ([link](https://extensions.libreoffice.org/en/extensions/show/english-dictionaries)). 

For Windows, after downloading, modify the file ending from `oxt` to `zip` to open. The files are paired together, one `*.dic` file with one `*.aff` file, both with the same file name. For `en-GB`, this will be `en_GB.dic` and `en_GB.aff` (this process should be similar for other operating systems). Copy the `*.dic` and `*.aff` file into the `spellcheck` folder within the transcript folder. Then re-open the transcript and select the desired dictionary for spellcheck from the dropdown list.

Uncompressed `*.dic` and `*.aff` files can be moved directly into the `spellcheck` folder.