glyph
=====
glyph is a data-interchange format with hypermedia elements.

introduction
============
glyph is derived from bencoding an

requirements
============

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC2119].

grammar
=======


::
	root :== (object whitespace*)+

	ws :== (space | tab | vtab | cr | lf)*

	nl :== cr | crlf

	object :== 
		  number
		| unicode
		| bytearray
		| float
		| datetime
		| nil
		| true
		| false
		| list
		| set
		| dictionary
		| node
		| extension

	number :== 'i' ws sign ascii_number ws 0x0a
	

	unicode :== 'u' ws ascii_number ws ':' utf8_bytes 
		where len(bytes) = ascii_number

	bytearray :== 'b' ws ascii_number ws ':' bytes
		where len(bytes) = ascii_number

	float :== 'f' ws hex_float ws 0x0a

	datetime :== 'd' utc_iso_datetime ws0x0a

	true :== 'T'
	false :== 'F'
	nil :== 'N'

	list :== 'L' ws (object ws)* 'E'
	set :== 'S' ws (object ws)* 'E'
	dict :== 'D' ws (object ws object ws)* 'E'

	node :== 'X' ws object ws object ws object 
	
	extension :== 'H' ws object ws object ws object

.. note

	may change terminator character to ';' 
	\n makes ugly query urls & lumpy output. better not having it sensitive.
	
	consider adding trailing character ';' to string, bytearrays for 
	nicer parsing.

numbers
-------

::
	number	encoding
	123	i123\n i+000123\n
	-123	i-123\n
	0	i0\n i-0\n i+0\n

integers of arbitrary precision, sign is optional.

.. note
	overflow behavior
	
unicode
-------

unicode element is a utf-8 encoded string. must not include
utf-16 surrogate pairs.

.. note
	should normalise to NFC according to rfc specs


..
	string 	encoding
	foo	u3:foo
	bar	u4:bar
	💩	u4:\xf0\x9f\x92\xa9

	n.b length is length of bytes, not length of string


bytearrays
----------

::
	bytes		encoding
	0x31 0x32 0x33	b3:123

float
-----

hexadecimal floating point notation is available
in java, c99 and python. see the appendix for how
this represenation works
::
	0.5	f0x1.0000000000000p-1\n 
	-0.5 	f-0x1.0000000000000p-1\n 
	inf	finf\n
	-inf	f-inf\n
	nan	fnan\n

n.b 'Infinity' ,'-Infinity', 'NaN' are legal forms too.

collections
-----------

::
	list	Li1\ni2\ni3\nE
	set	Si1\ni2\ni3\nE
	dict	Si1\ni2\ni3\ni4\nE

lists preserve order, 
sets, dicts don't - and do not have duplicate keys


.. note
	ordered dictionaries
	behaviour on duplicate keys 
	

datetimes
---------

datetimes are in iso-XXXX format. 

::
	datetime encoding

.. note
	timezones, periods?
	

node
----

nodes are three value tuples, name, attributes and content.
name SHOULD be a unicode string, attributes SHOULD be a dictionary,
content SHOULD be a list.

nodes can be used to represent an xml dom node

	<xml a=1>1</xml> Xu3:xmlDu1:ai1\n

extensions
----------
extensions are three value tuples.

name SHOULD be a unicode string, attributes SHOULD be a dictionary,
content SHOULD be a list.

extensions are data types with special handling, used to implement
forms and links

types/schemas
=============
	
form variables currently untyped. form has a values
attribute containing a list of string names


proposed change to allow optional types of form arguments, including
defaults.

extensions
==========

links
-----

building links
submitting links

forms
-----

building forms

submitting forms

resources
---------

errors
------

proposed

blobs
-----

proposed



encoding
========

building urls

handling resources, forms, links

handling extensions

parsers
=======

error handling
recovery

handling resources, forms, links

changes
-------

- initial use bencode
- booleans, datetimes added
- nil added
- forms, links, embeds added
- use b for bytestring instead of s
- remove bencode ordering constraint on dictionaries
- changed terminators/separators to '\n'
- resources added
- separator changed to ':' (new lines make for ugly query strings)

proposed changes
----------------

- change separator back to 'e' or ';' or ','
  - easier to read 

- blob extension type - aka bytestring with headers
  - remove bytestring entirely? (we use it, convienent for python) 
  - use case is for inling a response that isn't glyph

- error extension type
  - similar in use to the vnd.error proposal https://github.com/blongden/vnd.error
  - use as body content in 4xx, 5xx

- order preserving dictionary type
  - we use a list of lists for form schemas
  - hard to represent in many languages (but python, java, ruby have this)
  - current thinking: bad idea

- restrictions on what goes in dictionaries, sets
  - should use immutable collections? tuples?

- schema/type information for forms (aka values)

- caching information inside of resources	
  resources/embeds CAN contain control headers, freshness information
  add a glyph.refresh() call?

appendices
==========

url schema
----------

form urls are of the form /ObjectName/method?<glyph instance data>

note: ? breaks squid default config for caching.

caching
-------


mime type registration
----------------------


extension registry
------------------

hexadecimal floating point
--------------------------

normals, subnormals

nan, infinity, zero


