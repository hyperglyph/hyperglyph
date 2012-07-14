===============================
 glyph data model and encoding
===============================
:Author: tef
:Date: 2012-07-13
:Version: 0.2

glyph is a data-interchange format with hypermedia elements,
to describe machine readable web pages.

.. contents::


introduction
============

glyph is an encoding for remote procedure and method calls over
http, that supports returning arbitrary objects, and calling
methods on these at the client.

glyph is normally served over http, and used to offer
objects to the client. objects are described in terms
of hypermedia objects - links and forms. 

essentially, glyph is a format for machine readable webpages.
the server can translate objects into resources with forms,
and the client can translate this back into objects with methods.

glyph uses the mime type: 'application/vnd.glyph'

requirements
============

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC2119].

overview
========

glyph is designed for ease of implementation, ease of human inspection, and
based around bencoding from bittorrent. despite being a binary format, 
there are no byte ordering or endian issues.

underneath, glyph natively handles a variety of literals
(strings, bytes, numbers, floats, dates, booleans), 
collections (list, set, dictionary).


::

	data type	example			encoded

	integer		1			i1;
	unicode		"hello"			u5:hello;
	bytearray	[0x31, 0x32, 0x33]	b3:123;
	list		[1,2,3]			Li1;i2;i3;E
	set		{1,2,3}			Si1;i2;i3;E
	dictionary	{1:2, 2:3}		Di1;i2;i3;i4;E
	singleton	nil true false		N T F
	float		0.5			f0x1.0000000000000p-1; 
	datetime	1970-1-1 00:00 UTC	d1970-01-01T00:00:00.000Z;

glyph also supports a node tuple type (name, attributes, content).
there is also a special 'extension' type used to define objects with special
behaviour

mapping to http
===============

TODO: describe typical client/server interaction

how hypermedia encapsulates state

data types
==========

integers
--------

integers of arbitrary precision, sign is optional, and either '+' or '-'

::

	integer :== 'i' ws sign ascii_number ws ';'
	sign :== '+' | '-' | ''
	ascii_number :== <a decimal number as an ascii string>

	number	encoded:
	123	i123; i+000123;
	-123	i-123;
	0	i0; i-0; i+0;

note: if the decoder cannot represent the number without overflow, 
it SHOULD throw an error

unicode
-------

unicode element is a utf-8 encoded string. MUST not include
utf-16 surrogate pairs (JSON, Java, I'm looking at *you*)

::

	unicode :== 'u' ws ascii_number ws ':' utf8_bytes ';'
		where len(bytes) = int(ascii_number)

	utf8_bytes :== <the utf8 string>

	string 	encoding
	'foo'	u3:foo;
	'bar'	u4:bar;
	'💩'	u4:\xf0\x9f\x92\xa9;

	n.b length is length of bytes, not length of string

encoders SHOULD normalize strings to NFC, decoders MAY
normalize strings to NFC


bytearrays
----------

a byte array is a string of bytes. no encoding
is assumed.

::

	bytearray :== 'b' ws ascii_number ws ':' bytes ';'
		where len(bytes) = int(ascii_number)

	bytes			encoding
	[0x31,0x32,0x33]	b3:123;


singletons
----------

glyph has three singleton types: true, false, and nil::

	true :== 'T'
	false :== 'F'
	nil :== 'N'

nil SHOULD map to null or None or nil.

collections
-----------

glyph has three collection types, an ordered list,
an unordered set, and an unordered dictionary.

sets and dicts MUST NOT have duplicate items,
clients SHOULD throw an error.

::

	list :== 'L' ws (object ws)* 'E'
	set :== 'S' ws (object ws)* 'E'
	dict :== 'D' ws (object ws object ws)* 'E'

	object		encoding

	list(1,2,3)	Li1;i2;i3;E
	set(1,2,3)	Si1;i2;i3;E
	dict(1:2, 2:3)	Si1;i2;i3;i4;E

SUGGESTED: order preserving dictionary type

datetimes
---------

datetimes SHOULD be in utc, and MUST be in iso-8601/rfc3339 format::

	datetime :== 'd' iso_datetime ws ';'
	iso_datetime :== <normally: %Y-%m-%dT%H:%M:%S.%fZ >

	object		encoding

	1970-1-1	d1970-01-01T00:00:00.000Z;

encoders SHOULD use UTC timezone of 'Z',
decoders MAY only support UTC timestamps.

PROPOSED: allow utc offsets, allow string timezone

TODO: format variants, inconsistencies

float
-----

floating point numbers cannot be represented in decimal
without loss of accuracy. instead of using an endian
dependent binary format, we use a hexadecimal string

(note: hex floats are supported natively by python and java)

a floating point number in hex takes a number of formats::

	0.5	0x1.0000000000000p-1
	-0.5 	-0x1.0000000000000p-1 
	+0.0	0x0p0
	-0.0	-0x0p0
	1.729	0x1.ba9fbe76c8b44p+0

first there is an optional sign, '+' or '-', then
the prefix '0x' indicates it is in hex.
finally, a hex number and its decimal exponent,
separated by a 'p'. the exponent can have a sign,
and is a decimal number::

	float :== 'f' ws hex_float ws ';'

	float	encoding
	0.5	f0x1.0000000000000p-1; 
	-0.5 	f-0x1.0000000000000p-1; 
	0.0	f0x0p0;

special values, nan and infinity are serialized as strings::

	float		encoding
	infinity	finf; fInfinity; finfinity;
	-infinity	f-inf; f-infinity; f-Infinity;
	NaN		fnan; -fNaN

decoders SHOULD ignore case and MAY only check the prefix
of 'inf' rather than being exact.

hexadecimal floating point conversion is detailed in an appendix.

node
----

nodes are generic named containers for application use:
tuples of name, attributes and content objects.

name SHOULD be a unicode string, attributes SHOULD be a dictionary::

	node :== 'X' ws name_obj ws attr_obj ws content_obj 'E'

	name_obj :== string | object
	attr_obj :== dictionary | object
	content_obj :== object

decoders MUST handle nodes with arbitrary objects for
name, attributes and content

decoders normally transform nodes into wrapper objects
where object attributes are matched to the content_obj
i.e forwarding node[blah] and node.blah to content_obj[blah]

nodes can be used to represent an xml dom node::

	xml			encoded
	<xml a=1>1</xml>	Xu3:xmlDu1:ai1;E


extensions
----------

extensions are name, attr, content tuples, used internally within glyph
to describe objects with special handling or meaning, rather than
application meaning.

name SHOULD be a unicode string, attributes SHOULD be a dictionary::

	extension :== 'H' ws name_obj ws attr_obj ws content_obj 'E' 
	name_obj :== string | object
	attr_obj :== dictionary | object
	content_obj :== object

extensions are used to represent links, forms, resources, errors
and blobs within glyph.

decoders SHOULD handle unknown extensions as node types.

extensions
==========

the following extensions are defined within glyph

note: all names are unicode strings

link
----
a hyperlink with a method and url

- name 'link'
- attributes is a dictionary with the keys 'url', 'method'
- content is nil object 

links map to functions with no arguments.


embed
-----
a hyperlink with a method, url and the response embedded

- links with inline responses have the name 'embed'
  * attributes is a dictionary with the keys 'url', 'method'
  *  url and method are both unicode keys with unicode values.
- content is the inlined response.

PROPOSED: unify link and embed type.

embeds map to functions with no arguments

form
----

like a html form, with a url, method, expected form values.

- name 'form'
- attributes is a dictionary
  * MUST have the keys 'url', 'method' , 'values'
  * url and method are both unicode keys with unicode values.
  * values is a list of unicode names
- content is nil object

forms map to functions with arguments.
when submitting a form, the arguments
are encoded as a list, in the order given.

resource
--------

like a top level webpage. like in a node

- name 'resource'
- attributes is a dictionary,
  *  MAY have the keys 'url', 'name'
- content is a dict of string -> object
  * objects often forms

resources map to instances, where the content contains
forms mapping to the methods.

error
-----

errors provide a generic object for messages in response
to failed requests. servers MAY return them.

- name 'error'
- attributes is a dictionary with the keys 'logref', 'message'
- content SHOULD be a dict of string -> object, MAY be empty.

logref is a application specific reference for logging.
message is a unicode string


blob
----

blobs represent a typed bytestring. blobs can represent
inlined responses for data other than glyph objects.

- name 'blob'
- attributes is a dictionary,
  * MUST have the key 'content-type'
  * MAY have the key 'url'
- content is a bytearray

glyph servers can transform a response of a blob
into a http response with the given content-type and blob

glyph clients can return an response with an unknown encoding
as a blob


types/schemas
=============
	
form variables currently untyped. form has a values
attribute containing a list of string names

PROPOSED: some way to epress types on form inputs, default values

grammar
=======

::

	root :== ws object ws

	ws :== (space | tab | vtab | cr | lf)*

	object :== 
		  integer
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

	integer :== 'i' sign ascii_number ';'

	unicode :== 'u' ascii_number ':' utf8_bytes ';'
		where len(bytes) = int(ascii_number)

	bytearray :== 'b' ascii_number ':' bytes ';'
		where len(bytes) = int(ascii_number)

	true :== 'T'
	false :== 'F'
	nil :== 'N'

	list :== 'L' ws (object ws)* 'E'
	set :== 'S' ws (object ws)* 'E'
	dict :== 'D' ws (object ws object ws)* 'E'

	float :== 'f' hex_float ';'

	datetime :== 'd' iso_datetime ';'

	node :== 'X' ws name_obj ws attr_obj ws content_obj ws 'E'

	extension :== 'H' ws name_obj ws attr_obj ws content_obj ws 'E' 
	

encoding
========

TODO: expand with notes on encoder specifics

building urls

handling resources, forms, links

handling extensions

parsers
=======

TODO

error handling
recovery

handling resources, forms, links


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
	for a double - single floats have a different offset.
	
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

history
-------

- v0

- initial use bencode

	  json didn't support binary data
- booleans, datetimes added


- nil added

	  creature comforts

- forms, links, embeds added

  	hypermedia is neat

- use b for byte array instead of s

	  less confusing

- remove bencode ordering constraint on dictionaries

	  as there isn't the same dict keys must be string restrictions

- changed terminators/separators to '\n'

	  idea for using 'readline' in decoders, but made things ugly

- resources added

	  instead of using nodes to represent resources

- v0.1  - spec started

- blob, error type placeholders added

- separator changed to ':' ,changed terminator to ';' 

	  new lines make for ugly query strings
	  easier to read, and no semantic whitespace means easier pretty printing 

- blob extension type - aka byte array with headers

  	use case is for inling a response that isn't glyph

- error extension type

	  use as body content in 4xx, 5xx

- unicode normalization as a recommendation


- remove whitespace between prefix ... ;
- put a ';' at the end of strings - easier to read format
- put a 'E' at the end of nodes, extensions

- v0.2 - current

planned changes
---------------

- v0.3
- allow any iso datetime with offset in datetime type
- add timedelta/period type

	p<iso period format>;
	yes

- 0.4 -


- 0.5 grammar/encoding frozen - no more literals, collections added

- 0.6 schema/form inputs type

- 0.8 caching options defined
- 0.9 all extension type parameters defined
- 1.0 final

proposed changes
----------------

- unify link and embed extension

- node/ext becomes name, attrs, content* ?
	i.e allow a number of objects as the 'content'
  
- datetime with utc offset

- caching information inside of resources	

	  resources/embeds CAN contain control headers, freshness information
          specify key names as being optional

- schema/type information for forms (aka values)

	  (allow better mapping of args)


rejected changes
----------------

- datetime with string timezone
 	awkward, unstandardized. can use node type instead
	or an extension

- order preserving dictionary type
	use a list of lists

	hard to represent in many languages (but python, java, ruby have this)
	and hard to represent uniformly across languages

- restrictions on what goes in dictionaries, sets
	should use immutable collections? tuples?
	maybe a recommendation, but not a standard?


