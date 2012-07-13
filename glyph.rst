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

	number :== 'i' ws sign ascii_number ws ';'
	

	unicode :== 'u' ws ascii_number ws ':' utf8_bytes 
		where len(bytes) = ascii_number

	bytearray :== 'b' ws ascii_number ws ':' bytes
		where len(bytes) = ascii_number

	float :== 'f' ws hex_float ws ';'

	datetime :== 'd' utc_iso_datetime ws ';'

	true :== 'T'
	false :== 'F'
	nil :== 'N'

	list :== 'L' ws (object ws)* 'E'
	set :== 'S' ws (object ws)* 'E'
	dict :== 'D' ws (object ws object ws)* 'E'

	node :== 'X' ws object ws object ws object 
	
	extension :== 'H' ws object ws object ws object


numbers
-------

::
	number	encoding
	123	i123; i+000123;
	-123	i-123;
	0	i0; i-0; i+0;

integers of arbitrary precision, sign is optional.

.. note
	overflow behavior
	
unicode
-------

unicode element is a utf-8 encoded string. must not include
utf-16 surrogate pairs.

.. note
	should normalise to NFC according to rfc specs


::
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
	0.5	f0x1.0000000000000p-1; 
	-0.5 	f-0x1.0000000000000p-1; 
	inf	finf;
	-inf	f-inf;
	nan	fnan;

n.b 'Infinity' ,'-Infinity', 'NaN' are legal forms too.

collections
-----------

::
	list	Li1;i2;i3;E
	set	Si1;i2;i3;E
	dict	Si1;i2;i3;i4;E

lists preserve order, 
sets, dicts don't - and do not have duplicate keys


.. note
	ordered dictionaries
	behaviour on duplicate keys 
	

datetimes
---------

datetimes are in iso-XXXX format. 
currently UTC supported.

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

	<xml a=1>1</xml> Xu3:xmlDu1:ai1;

extensions
----------
extensions are three value tuples.

name SHOULD be a unicode string, attributes SHOULD be a dictionary,
content SHOULD be a list.

extensions are data types with special handling, used to implement
forms and links

hypermedia
==========

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

links have the name 'link'
attributes is a dictionary with the keys 'url', 'method'
content is none

building links
submitting links

embeds
------

links with inline resources have the name 'embed'
attributes is a dictionary with the keys 'url', 'method'
content is an object, normally a resource

forms
-----

have the name 'form'
attributes is a dictionary with the keys 'url', 'method'
content is none

building forms
submitting forms

resources
---------
have the name 'resource'
attributes is a dictionary with the keys 'url'
content is a dict of string -> object

errors
------

proposed. 'error'
attributes is a dictionary with the keys

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
=======

- initial use bencode
- booleans, datetimes added
- nil added
- forms, links, embeds added
- use b for bytestring instead of s
- remove bencode ordering constraint on dictionaries
- changed terminators/separators to ';'
- resources added
- separator changed to ':' (new lines make for ugly query strings)
- blob, error type placeholders added
- change separator to ';' 
  easier to read 


proposed changes
================

- put a ';' at the end of strings - easier to read format

- unify link and embed extension

- blob extension type - aka bytestring with headers
  remove bytestring entirely? (we use it, convienent for python) 
  use case is for inling a response that isn't glyph

- error extension type
  similar in use to the vnd.error proposal https://github.com/blongden/vnd.error
  use as body content in 4xx, 5xx

- order preserving dictionary type
  we use a list of lists for form schemas
  hard to represent in many languages (but python, java, ruby have this)
  current thinking: bad idea

- restrictions on what goes in dictionaries, sets
  should use immutable collections? tuples?

- schema/type information for forms (aka values)
  allow better mapping 

- caching information inside of resources	
  resources/embeds CAN contain control headers, freshness information
  add a glyph.refresh() call?

- datetime with offset, timezone
  allow non utc dates, but you need the utc offset
  optional string timezone

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


decimal:  0.5d::

	in network byte order

	offset:    0  8  16 32 40 48 56 64
	bytes:     3f e0 00 00 00 00 00 00


	sign bit: bit 0

	sign_bit = (byte[0] & 128) == 128   
	sign = 0 is sign_bit is 0
	       1 if sign_bit is 1

	sign bit of 0.5 is 0x3f & 128 = 0

	exponent: bits 1..12  (11 bits) as network order int 
	instead of signed, exponent is stored as exp+1023 if exp != 0
	
	raw_exponent = ((byte[0] &127) << 4) + ((byte[1]&240) >> 4)
	so raw_exponent = ((0x3f &127) << 4) + ((0xe0)>>4) = 1022

	n.b if raw exponent is 0, then exponent is 0.
	    if raw exponent is not 0, exponent is raw_exponent-1023

	exponent of 0.5 is -1 (1022-1023)

	fractional: bits 13..64  (52 bits) as unsigned network int

	fractional = [ byte[1]&15, byte[2], ...]

	fractional part of 0.5 is [0xe0&15, 0x00,0x00,...] is 0


	so hex is <SIGN>0x1.<FRACTIONAL>p<EXPONENT> where FRACTIONAL is in hex, exponent in decimal
	for normals.

	0.5 in hex:   0x1.0000000000000p-1 
	-0.5 in hex: -0x1.0000000000000p-1 


for subnormals and 0, the raw exponent is 0, and so the exponent is either::

	0, if the fractional part is 0 
	-1022, if the fractional part is non 0

these are formatted with a leading 0, not 1
