===========
 glyph rpc 
===========
:Author: tef
:Date: 2012-07-24
:Version: 0.5 (DRAFT)

glyph-rpc is a client-server protocol for interacting with
objects over http, sing machine readable web pages.

these pages are encoded using a data-interchange format
with hypermedia elements. the format is called glyph, and
uses the mime-type 'application/vnd.glyph'

.. contents::


requirements
============

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC2119].

introduction
============

A glyph-rpc server is a web server which serves up glyph
encoded pages. 

The server maps classes, instances, methods to URLs.
URLs are opaque to the client, beyond the initial URL.

A glyph-rpc client is a screen scraper which reads glyph
pages, and follows links and forms to interact with them.

These pages have named attributes, some containing data,
others containing hypermedia: links and forms. 
Links and forms map back to methods at the server.


glyph data model
================

glyph natively handles a variety of literals (strings, bytes, 
numbers, floats, utc datetimes, timedeltas, booleans), 
and collections (list, set, dict).  ::

	data type		example			encoded
	
	integer			1			i1;
	unicode			"hello"			u5:hello;
	bytearray		[0x31, 0x32, 0x33]	b3:123;
	list			[1,2,3]			Li1;i2;i3;;
	set			set(1,2,3)		Si1;i2;i3;;
	dict			{1:2, 2:4}		Di1;i2;i3;i4;;
	ordered_dict		ordered(1:2, 2:4)	Oi1;i2;i3;i4;;
	singleton		nil true false		N; T; F;
	float			0.5			f0x1.0000000000000p-1; 
	datetime		1970-1-1 00:00 UTC	d1970-01-01T00:00:00.000Z;
	timedelta		3 days			pP0Y0M3DT0H0M0S;

glyph also supports special data types:

- a 'node' tuple type (name, attributes, content).
- an 'extension' type used to define objects with special behaviour or meaning
- a 'blob' and 'chunk' type, used to attach large files to an object

the encoding format glyph aims to be: 

 - endian independent
 - straight forward to implement
 - allow human inspection

top level
---------

a glyph encoded message consists of a single object, optionally
followed by chunks ::
	
	root :== ws object ws (trailer ws)* 
	trailer :== (chunk | end_chunk)  
	
	ws :== (space | tab | vtab | cr | lf)*
	
	object :== integer | unicode | bytearray | float
		| datetime | timedelta
		| nil | true | false
		| list | set | dict | ordered_dict
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

glyph has four collection types, an ordered list,
an unordered set, and an ordered & unordered dictionary.

sets and dicts MUST NOT have duplicate items,
clients SHOULD throw an error.

::

	list :== 'L' ws (object ws)* ';'
	set :== 'S' ws (object ws)* ';'
	dict :== 'D' ws (object ws object ws)* ';'
	ordered_dict :== 'O' ws (object ws object ws)* ';'

	object			encoding

	list(1,2,3)		Li1;i2;i3;;
	set(1,2,3)		Si1;i2;i3;;
	dict(1:2, 3:4)		Di1;i2;i3;i4;;
	ordered_dict(1:2, 3:4)	Oi1;i2;i3;i4;;

lists, ordered_dicts MUST preserve ordering. dicts, sets have no ordering.

datetime
--------

datetimes MUST be in UTC, and MUST be in the following subset of iso-8601/rfc3339 format::

	datetime :== 'd' iso_datetime ';'
	iso_datetime :== <date: %Y-%m-%dT%H:%M:%S.%fZ>

	object		encoding

	1970-1-1	d1970-01-01T00:00:00.000Z;

encoders MUST use UTC timezone of 'Z'.  decoders MUST only support UTC timestamps,
but MAY support other offsets.


timedelta
---------

timedeltas MUST be in the following subset of iso-8601 period format::

	timedelta :== 'p' iso_period ';'
	iso_period :== <period:  pnYnMnDTnHnMnS>

	object			encoding

	3 days, 2 hours		pP0Y0M3DT0H2M0S;

encoders MUST present all leading 0s.

float
-----


floating point numbers cannot easily be represented 
in decimal without loss of accuracy. instead of using an endian
dependent binary format, we use a hexadecimal format from c99::

	float :== 'f' hex_float ';'

	float	encoding
	0.5	f0x1.0p-1; 
	-0.5 	f-0x1.0p-1; 
	0.0	f0x0p0;

a floating point number in hex takes a number of formats::

	0.5	0x1.0p-1
	-0.5 	-0x1.0p-1 
	+0.0	0x0p0
	-0.0	-0x0p0
	1.729	0x1.ba9fbe76c8b44p+0

special values, nan and infinity are serialized as strings::

	float		encoding

	Infinity	finf; fInfinity; finfinity;
	-Infinity	f-inf; f-infinity; f-Infinity;
	NaN		fnan; fNaN;

decoders MUST ignore case.
encoders MUST use 'inf' or 'infinity', not 'infin', 'in', etc.

details on the encoding and decoding of hex floats is covered in an appendix.

node
----

nodes are generic named containers for application use:
tuples of name, attributes and content objects.

name SHOULD be a unicode string, attributes SHOULD be a dictionary::

	node :== 'X' ws name_obj ws attr_obj ws content_obj ws ';'

	name_obj :== string | object
	attr_obj :== dict | object
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

	blob :== 'B' id_num ':' attr_dict ';'

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
----------

extensions are name, attr, content tuples, used internally within glyph
to describe objects with special handling or meaning, rather than
application meaning.

name SHOULD be a unicode string, attributes SHOULD be a dictionary::

	extension :== 'H' ws name_obj ws attr_obj ws content_obj ws ';' 
	name_obj :== string | object
	attr_obj :== dict | object
	content_obj :== object

extensions are used to represent links, forms, resources, errors
and blobs within glyph.

decoders SHOULD handle unknown extensions as node types.


extensions
==========

the following extensions are defined within glyph:

note: all strings are unicode strings, all dictionaries are unordered

link
----

a hyperlink with a method and url, optionally with an inlined response

- name 'link'
- attributes is a dictionary. MUST have the keys 'url', 'method'
 * method MUST be 'GET'
 * MAY have the entry 'inline' -> true | false
 * MAY have the entries 'etag' -> string,  'last_modified' -> datetime, 
- content is an object, which is either nil or the inlined response

links map to functions with no arguments. if the key 'inline' is in the
attributes and the associated value is true, then the function MAY
return the content object, instead of making a request.

if the 'etag', 'last_modified' keys are present, the client MAY
make a conditional GET request to see if the content object is fresh.

example::

	link(method="GET", url="/foo")

	Hu4:link;du6:method;u3:GET;u3:url;u4:/foo;;n;;

input
-----

an object that appears in forms, to provide information about a parameter.

- name 'input'
- attributes is a dictionary,
  *  MUST have the key 'name'
  *  MAY have the keys 'value', 'type'
- content is nil

the type attribute MAY be a unicode string, defining the expected
input, using the names defined in the gramar.

form
----

like a html form, with a url, method, expected form values.

- name 'form'
- attributes is a dictionary
  * MUST have the keys 'url', 'method' , 'values'
  * method SHOULD be 'POST'
  * url and method are both unicode keys with unicode values.
  * values is a list of parameter names,  unicode strings or input objects
  * MAY have the keys 'if_none_match' 'if_match'
- content is nil object

forms map to functions with arguments. function signatures map to the values
parameter. invoking a form object should make a POST request,
with the arguments encoded in glyph.

arguments are encoded in a list of list of `[name, value]` pairs,
using the parameter names in the form, in the same order.

the parameter names are either encoded as a unicode string,
or as an input object, with a name attribute. input

if the 'if_none_match' or 'if_match' attributes are present,
the client MUST add the corresponding HTTP headers to the request. 

example::

	form(method="POST", url="/foo", values=['a')

	Hu4:form;du6:method;u4:POST;u3:url;u4:/foo;u6:values;Lu1:a;;;N;;

resource
--------

like a top level webpage. in the host language, resource.foo
should map to the content dictionary. i.e r.foo is r.content[foo]

glyph maps urls to classes, instances and methods. when
you fetch a url that maps to an instance, a resource extension is returned

- name 'resource'
- attributes is a dictionary,
  *  MAY have the keys 'url', 'name'
- content is a dict of string -> object
  * objects usually forms

the content dictionary should have the instance data, as well
as forms or links which map to the instance methods.

example::

	class Foo {
		instance data a
		
		method b
	}

	resource(attributes={}, contents = {
		'a': foo.a,
		'b': form(.....)
	})

the specifics of url mapping are covered under `http`

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


collection
----------

an object that represents a remote collection of objects
and SHOULD behave like a normal collection in the host language.

- name 'collection'
- attributes is a dictionary,
  * MAY have the attributes 'range', 'get', 'del', 'set', 'next', 'prev', 'url','first','last'
- content is optionally an ordered collection, or nil

collections may optionally have a range of the items contained within.

..
	- size / size_hint
	- getitem, setitem, delitem
	- iter/next/prev
	- range/slice
	- oh god cursors D:
	- oh god url construction ?


reserved extensions
-------------------

extensions with the names: collection, integer, unicode, bytearray, float, datetime, timedelta, nil, true, false, list, set, dict, dict, ordered_dict, node, extension, blob are reserved.


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
		| dict
		| ordered_dict
		| node
		| extension
		| blob

	trailer :== (chunk | end_chunk)  


	integer :== 'i' sign ascii_number ';'

	unicode :== 'u' ascii_number ':' utf8_bytes ';' 
	            | empty_unicode
	  note: where len(bytes) = int(ascii_number)

	empty_unicode :=='u;'

	bytearray :== 'b' ascii_number ':' bytes ';' 
	              | empty_bytearray
	    note: where len(bytes) = int(ascii_number)

	empty_bytearray = 'b;'

	true :== 'T;'
	false :== 'F;'
	nil :== 'N;'

	list :== 'L' ws (object ws)* ';'
	set :== 'S' ws (object ws)* ';'
	dict :== 'D' ws (object ws object ws)* ';'
	ordered_dict :== 'O' ws (object ws object ws)* ';'

	float :== 'f' hex_float ';'

	datetime :== 'd' iso_datetime ';'
	timedelta :== 'p' iso_period ';'

	node :== 'X' ws name_obj ws attr_obj ws content_obj ws ';'

	extension :== 'H' ws name_obj ws attr_obj ws content_obj ws ';' 
	
	blob :== 'B' id_num ':' attr_dict ';'

	chunk :== 'c' id_num ':' ascii_number ':' bytes ';' 
	 note : where len(bytes) = int(ascii_number)

	end_chunk :== 'c' id_num ';' 

glyph-rpc http mapping
======================

mime type
---------

glyph uses the mime type: 'application/vnd.glyph'

url schema
----------

The server maps classes, instances, methods to urls.
URLs are opaque to the client, beyond the initial url

an example mapping::

	object		url
	a class		/ClassName/
	an instance 	/ClassName/?GlyphInstanceData
	a method	/ClassName/method?GlyphInstanceData
	a function	/Function/

There are no restrictions on how the server maps URLs, clients SHOULD NOT
not modify or construct URLs, but use them as provided.

requests
--------

HTTP requests should have the following headers:

- Accept, set to the glyph mime type

responses
---------

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


mime type registration
======================

TODO: profile option in mime type?

appendix: exadecimal floating point
===================================


a hex float has an optional sign, a hex fractional part and a decimal exponent part::
	
	float <optional sign>0x<hex fractional>e<decimal exponent with sign>
	sign is '-','+'
	hex fractional is <leading hexdigits>.<hexdigits> or 0a
	exponent has explicit sign '+'/'-' for numbers other than zero.

many languages support hex floats already::

	language	example

	C99		sprintf("%a",...) 	scanf("%a",...)
	Python		5.0.hex()		float.fromhex('...')
	Java 1.5	Double.toHexString(..)	Double.parseDouble(...)
	ruby 1.9	sprintf("%a", ...) 	scanf("%a", ...)		
	Perl 		Data::Float on CPAN

parsing a float can be done manually, using `ldexp`::


	# convert hhh.fff into a float
	fractional = int(leading,16) + (int(hexdigits,16) / (16**len(hexdigits)))
	# ldexp(f,e) is f + 2**e
	float = sign *  ldexp(fractional, int(exponent))

creating a float can be done manually using `frexp` and `modf`::
	
	# split the float up
	f,exp = frexp(fractional)
	# turn 0.hhhh->  hhhhh.0 
	f = int(modf(f * 16** float_width)[1])
	# construct hex float
	hexfloat = sign(f) +  '0x0.' hex(abs(f)) + 'p' + signed_exponent


appendix: changelog
===================

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

- v0.4

- added conditional-get in links

- added conditional-post in forms

- added ordered dict type

- ordered dictionaries

	hard to represent in many languages (but python, java, ruby have this)
	and hard to represent uniformly across languages

	counterpoint: iso periods are the same, have to write as if we've got better languages
		timedeltas are wildly inconsistent

	counterpoint: sets aren't there in other languages either

	pro: in ruby 1.9 dicts are ordered, want to be able to send them back and forth?
		remember - internal rpc usecase
		ruby doesn't have unordered hash type
	
- cleaned up hex float explanation, added better appendix

- added examples

- added input, collection stub

- v0.5

planned changes
---------------

- 0.5 grammar/encoding frozen - no more literals, collections added
- 0.6 add extensions:  schema/form inputs type, collections6
- 0.9 extensions frozen
- 1.0 final

proposed changes
----------------

- schema/type information for forms (aka values)

	formargs is a list of string names | input elements
	input elements have a name, type, optional default value

- collection types

	back/next links? url templates?

	metaobject protocols? i.e __next__ names on forms with special meaning
	for emulating built in types


rejected changes
----------------

- datetime with utc offset

	allow +hh/+hhmm/+hh:mm offsets instead of 'Z'
	maybe allow string timestamps
	need non utc usecases

- node/ext becomes name, attrs, content* ?

	i.e allow a number of objects as the 'content'
	effort

	maybe name, attrs, content?
	implicitly nil ? 
  

- datetime with string timezone

 	awkward, unstandardized. can use node type instead
	or an extension


- restrictions on what goes in dictionaries, sets

	should use immutable collections? tuples?
	maybe a recommendation, but not a standard?


