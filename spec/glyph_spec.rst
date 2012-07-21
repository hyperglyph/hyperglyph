===========
 glyph rpc 
===========
:Author: tef
:Date: 2012-07-14
:Version: 0.3 (DRAFT)

glyph-rpc is a client-server protocol for interacting with
objects over http, using machine readable web pages.

these pages are encoded using a data-interchange format
with hypermedia elements, called glyph, using the mime-type
'application/vnd.glyph'

.. contents::


introduction
============

glyph-rpc is normally served over http, and used to offer
objects to the client. objects are described in terms
of hypermedia objects - links and forms. 

underneath, glyph is a format for machine readable webpages.
the server can translate objects into resources with forms,
and the client can translate this back into objects with methods.

the client begins by fetching a page at a known url, and then
follows links and submits forms to receive new objects.

the links and forms contain a url and a method.

mime type
---------

glyph uses the mime type: 'application/vnd.glyph'

requirements
============

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC2119].


data types
==========

glyph is designed for ease of implementation, ease of human inspection, and
based around bencoding from bittorrent. despite being a binary format, 
there are no byte ordering or endian issues.

underneath, glyph natively handles a variety of literals
(strings, bytes, numbers, floats, utc datetimes, timedeltas, booleans), 
collections (list, set, dictionary).


::

	data type	example			encoded

	integer		1			i1;
	unicode		"hello"			u5:hello;
	bytearray	[0x31, 0x32, 0x33]	b3:123;
	list		[1,2,3]			Li1;i2;i3;;
	set		{1,2,3}			Si1;i2;i3;;
	dictionary	{1:2, 2:3}		Di1;i2;i3;i4;;
	singleton	nil true false		N; T; F;
	float		0.5			f0x1.0000000000000p-1; 
	datetime	1970-1-1 00:00 UTC	d1970-01-01T00:00:00.000Z;
	timedelta	3 days			pP0Y0M3DT0H0M0S;


glyph also supports special data types:

- a 'node' tuple type (name, attributes, content).
- an 'extension' type used to define objects with special behaviour or meaning
- a 'blob' and 'chunk' type, used to attach large files to an object

a glyph encoded message consists of a single object, optionally
followed by chunks.

::
	
	root :== ws object ws (trailer ws)* 
	trailer :== (chunk | end_chunk)  
	
	ws :== (space | tab | vtab | cr | lf)*
	
	object :== integer | unicode | bytearray | float
		| datetime | timedelta
		| nil | true | false
		| list | set | dictionary
		| node | extension | blob


integer
-------

integers of arbitrary precision, sign is optional, and either '+' or '-'

::
	
	integer :== 'i' sign ascii_number ';'
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

unicode element is a utf-8 encoded string. MUST NOT include
utf-16 surrogate pairs. Modified UTF-8/CESU-8 MUST NOT be used.

..
	(JSON, Java, I'm looking at *you*)

::

	unicode :== 'u' ascii_number ':' utf8_bytes ';' | empty_unicode
		where len(bytes) = int(ascii_number)
	
	empty_unicode :== 'u;'

	utf8_bytes :== <the utf8 string>

	string 	encoding
	''	u;
	'foo'	u3:foo;
	'bar'	u4:bar;
	'💩'	u4:\xf0\x9f\x92\xa9;

	n.b length is length of bytes, not length of string

Encoders SHOULD normalize strings to NFC, decoders MAY
normalize strings to NFC.

unicode should map to the native string type where applicable.


bytearray
---------

a byte array is a string of bytes. no encoding
is assumed.

::

	bytearray :== 'b' ascii_number ':' bytes ';' | empty_bytearray
		where len(bytes) = int(ascii_number)

	empty_bytearray = 'b;'

	bytes			encoding
	[0x31,0x32,0x33]	b3:123;
	[]			b;


singletons
----------

glyph has three singleton types: true, false, and nil::

	true :== 'T;'
	false :== 'F;'
	nil :== 'N;'

nil SHOULD map to null or None or nil.

collections
-----------

glyph has three collection types, an ordered list,
an unordered set, and an unordered dictionary.

sets and dicts MUST NOT have duplicate items,
clients SHOULD throw an error.

::

	list :== 'L' ws (object ws)* ';'
	set :== 'S' ws (object ws)* ';'
	dict :== 'D' ws (object ws object ws)* ';'

	object		encoding

	list(1,2,3)	Li1;i2;i3;;
	set(1,2,3)	Si1;i2;i3;;
	dict(1:2, 2:3)	Di1;i2;i3;i4;;

SUGGESTED: order preserving dictionary type

datetime
--------

datetimes MUST be in utc, and MUST be in the following subset of iso-8601/rfc3339 format::

	datetime :== 'd' iso_datetime ';'
	iso_datetime :== <date: %Y-%m-%dT%H:%M:%S.%fZ>

	object		encoding

	1970-1-1	d1970-01-01T00:00:00.000Z;

encoders MUST use UTC timezone of 'Z'.

decoders SHOULD only support UTC timestamps.

timedelta
---------

timedeltas MUST be in the following subset of iso-8601 period format::

	timedelta :== 'p' iso_period ';'
	iso_period :== <period:  pnynmndtnhnmns>

	object			encoding

	3 days, 2 hours		pP0Y0M3DT0H2M0S;

encoders MUST present all leading 0s.

float
-----

floating point numbers cannot easily be represented 
in decimal without loss of accuracy. instead of using an endian
dependent binary format, we use a hexadecimal format from c99

(in c99: printf("%a",0.5), in java Double.toHexString(), 
in python 0.5.hex(), in ruby printf/scanf)

a floating point number in hex takes a number of formats::

	0.5	0x1.0p-1
	-0.5 	-0x1.0p-1 
	+0.0	0x0p0
	-0.0	-0x0p0
	1.729	0x1.ba9fbe76c8b44p+0

first there is an optional sign, '+' or '-', then
the prefix '0x' indicates it is in hex.
finally, a hex number and its decimal exponent,
separated by a 'p'. the exponent can have a sign,
and is a decimal number::

	float :== 'f' hex_float ';'

	float	encoding
	0.5	f0x1.0p-1; 
	-0.5 	f-0x1.0p-1; 
	0.0	f0x0p0;

special values, nan and infinity are serialized as strings::

	float		encoding

	Infinity	finf; fInfinity; finfinity;
	-Infinity	f-inf; f-infinity; f-Infinity;
	NaN		fnan; fNaN;

decoders MUST ignore case.
encoders MUST use 'inf' or 'infinity', not 'infin', 'in', etc.


node
----

nodes are generic named containers for application use:
tuples of name, attributes and content objects.

name SHOULD be a unicode string, attributes SHOULD be a dictionary::

	node :== 'X' ws name_obj ws attr_obj ws content_obj ws ';'

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
	<xml a=1>1</xml>	Xu3:xmlDu1:ai1;;

in the host language, f n is a node, n.foo should map to content[foo].


extensions
----------

extensions are name, attr, content tuples, used internally within glyph
to describe objects with special handling or meaning, rather than
application meaning.

name SHOULD be a unicode string, attributes SHOULD be a dictionary::

	extension :== 'H' ws name_obj ws attr_obj ws content_obj ws ';' 
	name_obj :== string | object
	attr_obj :== dictionary | object
	content_obj :== object

extensions are used to represent links, forms, resources, errors
and blobs within glyph.

decoders SHOULD handle unknown extensions as node types.

blob
----

binary data can be attached to an object, to enable
requests to stream large data, similar to multipart handling.

client code should be able to send a filehandle as an argument,
and server code should expect blobs as a filehandle like 

this is done through blobs and chunks. a blob is a placeholder
for the content, and chunks appear after the root object. a client
can return multiple blobs, which will have seperate chunks attached.

::

	root :== ws object ws (trailer ws)* 
	object :== ... | blob | ... 
	trailer :== (chunk | end_chunk)  

	blob :== 'B' id_num ':' attr_dictionary ';'

	chunk :== 'c' id_num ':' ascii_number ':' bytes ';' 
	 note : where len(bytes) = int(ascii_number)

	end_chunk :== 'c' id_num ';' 

	id_num :== ascii_number

blobs have a unique numeric identifier, which is used to match
it to the chunks containing the data.  

attributes MUST be a dictionary:

- MUST have the key 'content-type'
- MAY have the key 'url'

for each blob, a number of chunks must appear in the trailer,
including a final end_chunk. chunks for different files
MAY be interweaved. 

a glyph server SHOULD transform a response of a solitary blob object into a 
http response, using the content-type attribute.

glyph clients SHOULD return an response with an unknown encoding as a blob,
and SHOULD set the url attribute of the blob object.

a blob object should expose a content_type property, and a file like
object. 

extensions
==========

the following extensions are defined within glyph

note: all names are unicode strings

link
----

a hyperlink with a method and url, optionally with an inlined response

- name 'link'
- attributes is a dictionary. MUST have the keys 'url', 'method'
 * method SHOULD be 'GET'
 * MAY have the key 'inline'
 * MAY have the keys 'etag', 'last-modified', 'cache-control'
- content is an object, which is either nil or the inlined response

links map to functions with no arguments. if the key 'inline' is in the
attributes and the associated value is true, then the function MAY
return the associated content object, instead of making a request.

if a link has the etag, last-modified attributes, clients SHOULD
perform a conditional GET, using the 'If-None-Match', 'If-Modified-Since'


form
----

like a html form, with a url, method, expected form values.

- name 'form'
- attributes is a dictionary
  * MUST have the keys 'url', 'method' , 'values'
  * method SHOULD be 'POST'
  * url and method are both unicode keys with unicode values.
  * values is a list of unicode names
  * MAY have the keys 'etag', 'last-modified', 'cache-control'
- content is nil object

forms map to functions with arguments. submitting a form should be calling 
a function in the host language.

when making a POST request, the data is a list of ('name', 'value') pairs.

if a form has the etag, last-modified attributes, clients SHOULD
perform a conditional POST, using the 'If-Match', 'If-Unmodified-Since'

resource
--------

like a top level webpage. in the host language, resource.foo
should map to the content dictionary. i.e r.foo is r.content[foo]

- name 'resource'
- attributes is a dictionary,
  *  MAY have the keys 'url', 'name'
  * MAY have the keys 'etag', 'last-modified', 'cache-control'
- content is a dict of string -> object
  * objects often forms

when a method on the server returns a Resource object,
for example, the GET() method on Resources returns self,
the server changes it to a resource extension.

the content dictionary should have objects for the instance
data, as well as forms to map to the instance methods.

error
-----

errors provide a generic object for messages in response
to failed requests. servers MAY return them.

- name 'error'
- attributes is a dictionary with the keys 'logref', 'message'
- MAY have the attribute 'url'
- content SHOULD be a dict of string -> object, MAY be empty.

logref is a application specific reference for logging, MUST
be a unicode string, message MUST be a unicode string

input
-----

PLACEHOLDER: for input form type

form variables currently untyped. form has a values
attribute containing a list of string names

PROPOSED: some way to epress types on form inputs, default values

reserved extensions
-------------------

extensions with the names collection, integer, unicode, bytearray, float, datetime, timedelta, nil, true, false, list, set, dictionary, node, extension, blob are reserved.


grammar
=======

::

	root :== ws object ws (trailer ws)* 

	ws :== (space | tab | vtab | cr | lf)*

	object :== 
		  integer
		| unicode
		| bytearray
		| float
		| datetime
		| timedelta
		| nil
		| true
		| false
		| list
		| set
		| dictionary
		| node
		| extension
		| blob

	trailer :== (chunk | end_chunk)  


	integer :== 'i' sign ascii_number ';'

	unicode :== 'u' ascii_number ':' utf8_bytes ';' | empty_unicode
	   note :   where len(bytes) = int(ascii_number)

	empty_unicode :=='u;'

	bytearray :== 'b' ascii_number ':' bytes ';' | empty_bytearray
		where len(bytes) = int(ascii_number)

	empty_bytearray = 'b;'

	true :== 'T;'
	false :== 'F;'
	nil :== 'N;'

	list :== 'L' ws (object ws)* ';'
	set :== 'S' ws (object ws)* ';'
	dict :== 'D' ws (object ws object ws)* ';'

	float :== 'f' hex_float ';'

	datetime :== 'd' iso_datetime ';'
	timedelta :== 'p' iso_period ';'

	node :== 'X' ws name_obj ws attr_obj ws content_obj ws ';'

	extension :== 'H' ws name_obj ws attr_obj ws content_obj ws ';' 
	
	blob :== 'B' id_num ':' attr_dictionary ';'

	chunk :== 'c' id_num ':' ascii_number ':' bytes ';' 
	 note : where len(bytes) = int(ascii_number)

	end_chunk :== 'c' id_num ';' 

http
====

HTTP requests should have the following headers:

- Accept, set to the glyph mime type

HTTP Responses MUST have an appropriate Content-Type, and
the code may have special handling:

- 201 Created. This is equivilent to returning a link
  as the body.

- 204, No Content. This is equivilent to a 200 with a nil as the body.
  A server SHOULD change a nil response into a 204
  A client MUST understand a 204 as a nil response.

- 303 See Other. Redirects should be followed automatically,
  using a GET. A server SHOULD allow methods to return a redirect

A server SHOULD allow gzip encoding, and clients MUST understand
gzip encoding.

Clients SHOULD throw different Errors for 4xx and 5xx responses.


appendices
==========

url schema
----------

URLs are opaque to the client, beyond the initial url. Normally
The server maps objects to urls, using something like this::

	/ObjectName/method?<glyph instance data>

There are no conditions on the format of URLs, clients MUST
not modify them. 

caching
-------

mime type registration
----------------------

TODO: profile option in mime type?


extension registry
------------------


changelog
=========

history
-------

glyph started out as a simple encoding for rpc over http,
before embracing hypermedia.

- unversioned

	started with bencode with a 's' prefix on strings
	json didn't support binary data without mangling
	didn't support utf-8 without mangling 

- booleans, datetimes, nil added

	creature comforts

- forms, links, embeds added

  	hypermedia is neat

- use b for byte array instead of s

	less confusing

- remove bencode ordering constraint on dictionaries

	as there isn't the same dict keys must be string restrictions


- changed terminators/separators to '\n'

	idea for using 'readline' in decoders, but made things ugly

- sets added
	
	creature comforts

- used utf-8 strings everywhere instead of bytestrings

	python made it easy not to care about using unicode.


- resources added

	instead of using nodes to represent resources
	use extension type

- v0.1 

	encoding spec started in lieu of implementation based
	specification. declare current impl 0.1

- blob, error types added
	
	blob can be used to encapsulate mime data.
	errors as a generic template for error messages.

- v0.2

- separator changed to ':' ,changed terminator to ';' 

	new lines make for ugly query strings, 
	and no semantic whitespace means easier pretty printing 

- unicode normalization as a recommendation

	perhaps should be mandatory.

- remove whitespace between prefix ... ;
	
	allowing whitespace inside objects is confusing
	for non container types.

- add redundant terminators
	
	put a ';' at the end of strings, bytearrays
	put a 'E' at the end of nodes, extensions
	consistency and ease for human inspection of data

- v0.3

- made utc mandatory rather than recommendation

- encoding consolidation
	use ; as terminator everywhere
	TFN -> T;F;N;

- add timedelta/period type:
	p<iso period format>;
	problems: timedeltas are sometimes int millis or float days or specific object

- unify link and embed extension
	add 'cached':True as attribute
	means content can be returned in lieu of fetching

- blob/chunks as attachments for large file handling
	add top level blob, chunk type

- empty versions of bytestring, unicode

planned changes
---------------

- 0.4

- 0.5 grammar/encoding frozen - no more literals, collections added

- 0.6 schema/form inputs type

- 0.8 caching options defined
- 0.9 all extension type parameters defined
- 1.0 final

proposed changes
----------------

- caching information inside of resources	

	resources/embeds CAN contain control headers, freshness information
        specify key names as being optional
	expires? cache-control? etag last_modified

- schema/type information for forms (aka values)

	formargs is a list of string names | input elements
	input elements have a name, type, optional default value

rejected changes
----------------

- datetime with utc offset

	allow +hh/+hhmm/+hh:mm offsets instead of 'Z'
	maybe allow string timestamps
	need non utc usecases

- node/ext becomes name, attrs, content* ?

	i.e allow a number of objects as the 'content'
	effort
  

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


