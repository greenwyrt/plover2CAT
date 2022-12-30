# How to create headers and footers for export

Plover2CAT will add headers and footers for export formats which support them.

Header and footer text can be added using the `Headers` and `Footers` input fields under `Page Layout` in the Toolbox dock. Three text inputs correspond to the left, center and right positions for the header and footer. Text entered in the `Left` input field will be left aligned, text in the `Center` will be center aligned and so on. 

To insert a page number into the header/footer, use %p. This can be combined with other text strings. For example, `Page %p` will become `Page 1` on page one, `Page 2` on page two and so on.

Note that the user has to manage the length of text in the header/footer. If there is a long string in the left header position, and also something for the left center position, the long string will overwrite the center text.