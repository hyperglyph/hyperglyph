glyph serialization
===================

glyph is really just a serialization format, that contains hypermedia
such as forms, links and embeds.

glyph is based upon netstrings, and bencoding. it is a binary encoding
that is not endian dependent.

the content type is currently application/vnd.glyph
(one day i'd like to drop the vnd.)

plain datatypes
---------------

glyph supports
-utf8 strings
-byte arrays
-integers 
-iso datetimes (in utc)
-doubles/floats
-lists
-sets
-dicts
-true, false
-none/nil/null
-xml style nodes (name, attr, children) tuples
-hypermedia


hypermedia
----------

glyph currently supports 4 types of hypermedia

links - nodes with a url & method

embeds - links with a cached copy of the resource

forms - nodes with a url, method and a list of fields

rsources - nodes that represent a top-level resource, containing a url, and the contents


future work
-----------

considering ordered dictionaries, 
timezone support, time period support
better form support - optional defaults.
embed, resources have expiry information
resources have method to refresh contents
mime blocks? bytestrings with content-types?


specifics
---------

all datatypes are encoded into a byte string,
with some prefix ascii character to indicate 
the type

e.g
	u5:hello is a utf-8 string
	b5:world is a byte string 

strings!:
	utf-8 string -> u <byte len> \x0a <utf-8 string>
bytes!
	byte array -> b <byte len> \x0a  <byte array>

numbers:
	utc datetime -> d %Y-%m-%dT%H:%M:%S.%fZ \x0a
		note: currently only UTC times supported,
			  so all datetimes must end with Z

	num -> i <number> \x0a
		arbitrary precision whole number

	float -> f <float in hex> \x0a
		float or double - the hex format is from
		c99 (-)0xMANTISSAp(-)EXPONENT
	   
		

collections:
	list -> L <item> <item> <item> <item>....E
		
	dict -> D <key> <value> <key> <value>....E
		no duplicates allowed

	set  -> S <item> <item> <item> <item>....E
		no duplicates


singleton datatypes:
	true -> T
	false -> F
	none -> N

xml like three item tuples (name, attributes, content)
	node -> X<name item><attr item><content item>
		an object with a name, attributes and content
			attributes is nominally a dict.
			content nominally list
		think html5 microdata like

hypermedia types/extensions: 
	ext -> H<name item><attr item><content item>
		like a node, but contains url, method, possibly form values.

currently the following extensions are defined:
	resource, link, form and embed

	all dictionary keys *should* be utf-8

	link:   
		name is "link"
		attr is a dict, containing the following keys:
			url, method
			
		content is None

	form:   
		name is "form"
		attr is a dict, containing the following keys:
			url, method
			
		content is currently a list of names
		for the form to submit

		currently to submit a form, a dictionary is sent back

	embed
		name is "embed"
		attr is a dict, containing the following keys:
			url, method
			
		content is the object that would be returned
		from fetching that link

	
	resource
		name is "resource"
		attr is a dict, containing the following keys:
			url

		content is a dict of resource attributes
			often forms
			

notes
-----
all strings are in utf-8.
should be no bytestrings in dicts?
			

whitespace/newlines
-------------------
parser SHOULD ignore whitespace when it doesn't change
semantics i.e
	i 123 \n, i123\n, i 123\n, i123 \n, all same 

includes whitespace between items

parser MUST treat CRLF as LF - where LF is used
as a terminator.
	i.e i123\r\n and i123\n are the same




unordered collections (dict/set)
--------------------------------
for the unordered collections, it is recommended
to order them in some way, such that the serializing
is consistent within the library, i.e

	dump(dict) equals dump(parse(dump(dict)))

but the ordering is ignored when reading.


