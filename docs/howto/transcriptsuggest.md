# Generate suggestions from transcript

Plover2CAT will analyze the existing transcript for common n-grams and uncommon words in **Dictionary > Transcript Suggestions**.

## Choice of search

There are three types of search: 1) N-gram, 2) words, and 3) both. Select one type, then change subsequent options outlined below.

## Word search

Plover2CAT presents any words occurring more than the value in the minimum occurrence field, and if they exist in the SCOWL American English Words list with a value greater than the one selected in the `SCOWL Size Filter`. 

SCOWL sizes are ranked so the lower the size value of the word, the more common the word is. Setting the size higher means more words are filtered out, and only rare words are shown. Any words which do not exist in the word list are also shown. If the `SCOWL Size Filter` value is not set, then only a small set of 166 English stop words from Wikipedia are filtered out.

## N-gram search

Plover2CAT searches the transcript for n-grams from the minimum n-gram length to the max n-gram length but *only if* they occur more times than the value in the minimum occurrence field.

The minimum n-gram length is 2. While it is possible to set a high maximum n-gram length, for speed purposes, a reasonable value should be used.

## Generate suggestions

Click `Generate` to analyze the transcript with the search type selected. The table will show the word/n-gram in the first column, the first found existing outline in the second column, and alternative outlines in the third column.

## Add to dictionary

Edit the outline for the word/n-gram if needed or it is blank. Then select the row and click `To Dictionary`. 
