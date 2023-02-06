# Transcript data formats

The Rich Text Format (Court Reporting Extension) is the most commonly used data exchange format between professional CAT software as it is able to hold text, stroke, time, and dictionary data. Revision one (and the only) came out in 1995 and has not changed since. 

As part of the spec, vendors could add their own extensions. Consequently, RTF/CRE files from one CAT software may be imported into another but on a limited basis if vendor extensions are used and not documented publically. 

The RTF/CRE spec was created before the beginnings of XML, though both SGML and HTML were available. There are some benefis of basing the exchange format on RTF, such as it being plain-text (most word processors used binary formats back then), combining formatting and content in one document, and able to be viewed with WordPad and other word processors (steno data was put into ignored groups and therefore did not appear).

Most modern word processors save their data in XML-based formats such as the Open Office XML and Open Document Format. These modern specs have expanded on the features available in the RTF spec (that was last updated in 2008) and are better supported in terms of open source code for parsing and writing. Even if specific packages are not written for the XML format, it is still possible to use general XML parsers to create XML files. In comparison, open souce RTF parsers and writers are lacking in support and are rarely fully featured. 

Even though XML formats such as Open Document Format are easily parsable and well-supported, Plover2CAT uses JSON files for storing data, primarily for readability and the ease of conversion in Python. JSON files can be easily parsed into dictionary objects and it is considerably to manipulate dictionary objects in Python than XML documents. 

