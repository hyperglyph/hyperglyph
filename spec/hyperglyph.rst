============
 hyperglyph 
============
:Author: tef
:Date: 2012-08-12
:Version: 1.0

hyperglyph is a client/server protocol which
exposes application objects over http, as machine
readable web pages.

these pages are encoded using hyperglyph: a data interchange 
format which can handle strings, numbers, collections. 

The server maps classes, instances, methods to URLs,
and translates instances and methods to pages and forms.

The client browses the server, using forms to invoke
methods.

1.0 is not backwards compatible with 0.x.


.. contents::


requirements
============

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC2119].

data model
==========

hyperglyph natively handles a variety of literals (strings, bytes, 
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
	float			0.5			f0x1.0p-1;  or f0.5;
	datetime		1970-1-1 00:00 UTC	d1970-01-01T00:00:00.000Z;
	timedelta		3 days			pP0Y0M3DT0H0M0S;

hyperglyph also supports special data types:

- an 'extension' type used to define objects with special behaviour or meaning
- a 'blob' and 'chunk' type, used to encode large files

the encoding format hyperglyph aims to be: 

- endian independent
- straight forward to implement
- allow human inspection

top level
---------

a hyperglyph encoded message consists of a single object, optionally
followed by chunks ::
	
	root :== ws object ws (trailer ws)* 
	trailer :== (chunk | end_chunk)  
	
	ws :== (space | tab | vtab | cr | lf)*
	
	object :== integer | unicode | bytearray | float
		| datetime | timedelta
		| nil | true | false
		| list | set | dict | ordered_dict
		| extension | blob


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

encoders MUST NOT produce numbers with leading 0s. decoders MUST
ignore leading zeros.

unicode
-------

a unicode element is a utf-8 encoded string. MUST NOT include
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
is assumed, i.e, an octet-stream.

::

	bytearray :== 'b' ascii_number ':' bytes ';' | empty_bytearray
		where len(bytes) = int(ascii_number)

	empty_bytearray = 'b;'

	bytes			encoding
	[0x31,0x32,0x33]	b3:123;
	[]			b;


singletons
----------

hyperglyph has three singleton types: true, false, and nil::

	true :== 'T;'
	false :== 'F;'
	nil :== 'N;'

nil SHOULD map to null or None or nil.

collections
-----------

hyperglyph has four collection types, an ordered list,
an unordered set, and an ordered & unordered dictionary.

sets and dicts MUST NOT have duplicate items,
clients SHOULD not recover.

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

floating point numbers can be represented in decimal or
hexadecimal. hexadecimal floats were introduced by C99,
and provide a way for accurate, endian free 
representation of floats. for example::


	float	hex			decimal

	0.5	0x1.0p-1		f0.5;
	-0.5 	-0x1.0p-1 		f-0.5;
	+0.0	0x0p0			f+0.0;
	-0.0	-0x0p0			f-0.0;
	1.729	0x1.ba9fbe76c8b44p+0	f1.729;

hex floats are `<sign.?>0x<hex>.<hex>e<sign><decimal>`, where
the first number is the fractional part in hex, and the latter is the exponent
in decimal.  details on the encoding and decoding of hex floats is covered in an appendix.

hyperglyph uses hex or decimal floats, except for the special floating
point values: nan and infinity::

	float :== 'f' hex_float ';' | 'f' decimal_float ';' | 'f' named_float ';'

	float		encoding	
	0.5		f0x1.0p-1; 	or	f0.5;
	-0.5 		f-0x1.0p-1; 	or 	f-0.5;
	0.0		f0x0p0;		or 	f0.0;

	Infinity	finf; 	or 	fInfinity;	or 	finfinity;
	-Infinity	f-inf; 	or 	f-infinity;	or	f-Infinity;
	NaN		fnan; 	or 	fNaN;

decoders MUST ignore case.
encoders MUST use 'inf' or 'infinity', not 'infin', 'in', etc.

decoders MUST support hex and decimal floats. encoders
SHOULD use hex floats instead of decimal.


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

a hyperglyph server SHOULD transform a response of a solitary blob object into a 
http response, using the content-type attribute.

hyperglyph clients SHOULD return an response with an unknown encoding as a blob,
and SHOULD set the url attribute of the blob object.

a blob object should expose a content_type property, and a file like
object. 

extensions
----------

extensions are name, attr, content tuples, used internally within hyperglyph
to describe objects with special handling or meaning, rather than
application meaning.

name SHOULD be a unicode string, attributes SHOULD be a dictionary or ordered dictionary::

	extension :== 'X' ws name_obj ws attr_obj ws content_obj ws ';' 
	name_obj :== unicode
	attr_obj :== dict | ordered_dict
	content_obj :== object

extensions are used to represent links, forms, resources, errors
and blobs within hyperglyph.


extensions
==========

the following extensions are defined within hyperglyph::

	link, input, form, resource, error

for these extensions, name MUST be a unicode string, attributes MUST be a dictionary or ordered dictionary.
 
link
----

a hyperlink with a method and url, optionally with an inlined response.
links MUST be safe (and idempotent) requests.

- name 'link'
- attributes is a dictionary. MAY have the keys 'method', 'url'

  * url MAY be relative, to the response or a parent object.
  * MAY have the entry 'inline' -> true | false
  * MAY have the entries 'etag' -> string,  'last_modified' -> datetime, 

- content is an object, which is either nil or the inlined response


links normally describe a GET request, under http. links SHOULD be 
transformed into functions in the host language, where invoking
the function makes the request.

if the key 'inline' is in the attributes and the associated value is true, 
then the function MAY return the content object, instead of making a request.

if the 'etag', 'last_modified' keys are present, the client MAY
make a conditional request to see if the content object is fresh.

specific details on how to handle methods and urls and invoke a response is detailed
in the mapping for that protocol. http mapping is defined later.

example::

	link(method="GET", url="/foo")

	Xu4:link;Du6:method;u3:GET;u3:url;u4:/foo;;n;;

the url MAY be relative to the page url, or to a parent object.

if the url is empty or not present, it is assumed to be the parent
object url or the response url.if the url is present, the client MUST
use this url for resolving relative links in any contained
links, forms and other extensions, within the content object.

form
----

like a html form, with a url, method, expected form values.
forms make unsafe requests.

- name 'form'
- attributes is a dictionary

  * MUST have the keys 'url', 'method' , 'values'

    - urls MAY be relative to the base url or a parent object.
    - url and method are both unicode keys with unicode values.
    - values is a list of parameter names,  unicode strings or input objects

  * MAY have the key 'headers'

    - headers is a dictionary of unicode strings

  * MAY have the key 'envelope'
  
    - a unicode string, describing how to construct a request

  * MAY have the key 'content_type'

    - if present, MUST be the hyperglyph mime type.

- content is nil object

forms normally describe a POST request, under http. forms SHOULD be 
transformed into functions in the host language, where invoking
the function with arguments makes the request.

the 'values' attribute describes the arguments for the request,
as a list of names or input elements. the client uses this list
to constuct the data for the request.

the envelope attribute describes how to build a request from
the url, method, and form argument names/values. envelopes
are defined by the protocol mapping. for HTTP, 'form','blob', 'none', and 'query' are defined:

for the envelope 'form', the body of the request is a ordered dictionary `{name:value, name1: value1}`,
where the names are in the same order as the 'values' attribute,
using the unicode string as the name, or the input element's name
attribute. 

for the envelope 'blob', the form must have a single argument, and the body
of the request is the content of the blob object.

for the envelope 'none', the form must take no arguments, and there is no
request body.

for the envelope 'query', the form arguments are serialized like in 'form',
but the data is encoded in the request url, rather than the request body.

if the envelope is missing, then the default mapping for the method is used.

specifics of envelopes, their interaction with methods, 
along with building a request, are covered in the http mapping below.
 

example::

	form(method="POST", url="/foo", values=['a'])

	Xu4:form;Du6:method;u4:POST;u3:url;u4:/foo;u6:values;Lu1:a;;;N;;

the url MAY be relative to the page url, or to a parent object.

if the url is empty or not present, it is assumed to be the parent
object url or the response url.if the url is present, the client MUST
use this url for resolving relative links in any contained
links, forms and other extensions, within the content object.

the header attribute is a dictionary of headers clients SHOULD add to the
request, if they are allowed by the mapping. if the client cannot add
the header, the request MUST not be made, and an ERROR must be raised.

input
-----

an object that appears in forms, to provide information about a parameter.

- name 'input'
- attributes is a dictionary,

  *  MUST have the key 'name'
  *  MAY have the keys 'value', 'type', 'envelope'

- content is nil

the value attribute is the default value for this argument.
if a client does not provide a value for this argument, the
default SHOULD be used instead.

the 'type', 'envelope' parameters are reserved.


..
	1.1:
	the type attribute, if present, SHOULD be unicode string,
	defining the expected type for this parameter.

	clients MAY parse this string to find out the expected
	type for the argument. the intent is for building browsers
	or inspectors for apis. clients MAY use this information
	to convert a parameter. if the type is not present or known, the client can
	assume it to be 'object'.

	types are defined for the names in the grammar::

		object integer unicode bytearray float
		datetime timedelta nil true false
		list set dict ordered_dict
		extension blob

	additionally, the type 'bool' is defined to mean 'true' or 'false'.
	types may have a trailing '?' to indicate that nil is also acceptable

	types may take some other types as parameters, this is indicated by
	the form `typename/arity`. so, the type `integer list/1` represents a 
	`list` of `integer`. the types are specified as a space separated list
	in postfix order::

		'unicode'			a unicode string 
		'integer?'			an integer or nil
		'list/0'				a list of objects
		'string list/1'  			a list of strings
		'object string dict/2' 		a dict of string to object
		'float list?/1 string dict/2' 	a dict of string, to nil or a list of floats
		'float integer list/1 dict/2'	a dict of a integer list, to a float



resource
--------

like a top level webpage. in the host language, resource.foo
should map to the content dictionary. i.e r.foo is r.content[foo]

hyperglyph maps urls to classes, instances and methods. when
you fetch a url that maps to an instance, a resource extension is returned

- name 'resource'
- attributes is a dictionary,
  *  MAY have the keys 'url', 'name', 'profile'
    - profile, name, url all unicode strings.
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

if the url is empty or not present, it is assumed to be the parent
object url or the response url.if the url is present, the client MUST
use this url for resolving relative links in any contained
links, forms and other extensions, within the content object.

the 'profile' attribute, if present SHOULD be a URI
relating to the type of resource returned.

error
-----

errors provide a generic object for messages in response
to failed requests. servers MAY return them.

- name 'error'
- attributes is a dictionary with the keys 'logref', 'message'
- MAY have the attributes 'url', 'code'
- content SHOULD be a dict of string -> object, MAY be empty.

logref is a application specific reference for logging, MUST
be a unicode string, message MUST be a unicode string

if the error object has a 'url' attribute, the client MUST
use this url for resolving relative links in any contained
links, forms and other extensions, within the content object.

collection
----------

a reserved extension type. this will provide a 'pagination' alike
mechanism for browsing collections on the server.

- name 'collection'
- attributes is a dictionary,
- content is optionally an ordered collection, or nil

if the collection has a 'url' attribute, the client MUST
use this url for resolving relative links in any contained
links, forms and other extensions.


reserved extensions
-------------------

the following extension names are reserved, and should not be used for 
application or vendor specific extensions::

	integer, unicode, string, bytearray, float, datetime,
	timedelta, nil, true, false, list, set, dict, 
	ordered_dict, extension, blob, bool, 	
	request, response


http mapping
============

hyperglyph uses HTTP/1.1, although mappings to other protocols,
or transports is possible.

mime type
---------

hyperglyph data has the mime type: 'application/vnd.hyperglyph'

gzip
----
A server SHOULD allow gzip encoding, and clients SHOULD understand
gzip encoding.

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

clients MUST support 'GET' and 'POST' methods.

the client MAY support 'PATCH', 'PUT', or 'DELETE', directly, 
or using POST, with the the original method name in a header  called 'Method'.

Servers MUST treat the `Method` header as the method for the request,
if present.

HTTP requests should have the following headers:

- Accept, set to the hyperglyph mime type, if not overridden

forms and links MAY provide the following headers in requests:

- forms can have the headers 'If-None-Match', 'Accept', 'If-Match', 'If-Unmodified-Since', 'If-Modified-Since'
- links can have the headers 'Accept'

responses
---------

HTTP Responses MUST have an appropriate Content-Type, and
the code may have special handling:

- 201 Created. Client should treat this as 
  returning a link, with the url from the Location header

- 204, No Content. This is equivilent to a 200 with a nil as the body.
  A server SHOULD change a nil response into a 204
  A client MUST understand a 204 as a nil response.

- 303 See Other. Redirects should be followed automatically,
  using a GET. A server SHOULD allow methods to return a redirect


Clients SHOULD throw different Errors for 4xx and 5xx responses,
the body of error responses SHOULD be a error extension object.

a hyperglyph server SHOULD transform a response of a solitary blob object into a 
http response, using the content-type attribute.

hyperglyph responses MAY use relative urls.

the methods `OPTIONS`, `TRACE`, `HEAD` are not used. 

links
-----

links MUST always be safe, idempotent requests. the methods
`PUT`, `POST`, `DELETE`, `PATCH`, are not valid.


if the method is not present, it is assumed to be 'GET'. 


forms
-----

forms represent unsafe requests by default, and if the method is
not present, it is assumed to be 'POST'. 


form envelopes
--------------

for 'none', the request MUST have no body, and the form MUST NOT have arguments.
if arguments are present, clients SHOULD raise an error.

for 'blob', the client MUST send the blob contents as the request body,
setting the appropriate content-type header. The client
MUST add the header 'Content-Disposition: form-data; name="...";',
with the name of the input set.

for 'form', the request body MUST be a hyperglyph encoded ordered
dictionary of (name->value) entries.

for 'query', the request MUST have no body, and the request url is
constructed from the form url, and the form arguments as the query string.

this query string is a urlencoded, hyperglyph encoded
ordered dictionary, of (name->value) entries.
i.e. /form/url/without/query?Ou4%3Aname%3Bu5%3Avalue%3B%3B

form: POST
----------

for the 'POST' method, the envelopes 'none', 'form', 'blob' are allowed.
POST methods default to 'form'. POST requests may send an empty 
body, e.g 'Content-Length: 0', instead of no body.

form: GET
---------

for the 'GET'  method, the envelopes 'none', 'query' are allowed,
the default is 'query'. 

forms with 'GET' methods MUST NOT send conditional-get
requests as a result of headers provided in the form.

GET requests MUST not have message bodies.

form: PUT
---------

for the 'PUT' method, the envelopes 'blob', 'form' are allowed,
and work like 'POST'. if not present, the default is 'blob'

if the client cannot send a PUT request, it MAY send a POST
request with the header `Method: PUT`. 


form: DELETE
------------

DELETE allows the envelopes 'none', 'query', 'blob', 'form',
and uses them like POST

DELETE methods default to 'none'. DELETE requests may send an empty 
body, e.g 'Content-Length: 0', instead of no body.

if the client cannot send a DELETE request (or a DELETE request with
a body), it MAY send a POST request with the header `Method: DELETE`. 


form: PATCH
-----------

for the 'PATCH' method, the envelopes 'blob', 'form' are allowed,
and work like 'POST'. if not present, the default is 'blob'

if the client cannot send a PATCH request, it MAY send a POST
request with the header `Method: PATCH`. 


appendix
========

mime type registration
----------------------

TODO: profile option in mime type?

grammar
-------

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

	extension :== 'X' ws name_obj ws attr_obj ws content_obj ws ';' 
	
	blob :== 'B' id_num ':' attr_dict ';'

	chunk :== 'c' id_num ':' ascii_number ':' bytes ';' 
	 note : where len(bytes) = int(ascii_number)

	end_chunk :== 'c' id_num ';' 

hexadecimal floating point
--------------------------

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

..
	creating a float can be done manually using `frexp` and `modf`::
		# split the float up
		f,exp = frexp(fractional)
		# turn 0.hhhh->  hhhhh.0 
		f = int(modf(f * 16** float_width)[1])
		# construct hex float
		hexfloat = sign(f) +  '0x0.' hex(abs(f)) + 'p' + signed_exponent

	TODO: fix this, it's broken


changelog
=========

history
-------

hyperglyph started out as a simple encoding for rpc over http,
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
  
  - schema/type information for forms (aka values)
  
  	formargs is a list of string names | input elements
  	input elements have a name, type, optional default value
  
  - collection types

- 0.5 grammar/encoding frozen - no more literals, collections added

  - relative url handling (e.g resources are used as base url for contained links)
  
  - input type parameters added
  
  - adding a header argument
  
  - adding arity to type descriptors 
  
  - define behaviour for other HTTP methods on links, forms

- 0.6 
  
  - leading zeros ignored for integers.
  
  - ordered dictonary used for form data
  
  - collection type is now reserved
  
  - profile is only on resources

- 0.7

  - allow decimal floats because i'm not that cruel

  - relative url handling is constrained to the content object within extensions

  - form envelope types

- 0.8

  - types removed

  - removed nodes - xml should be inside a blob, or a new extension type.

  - removed non http method support. 

  - added content-type to forms

- 0.9
 
  - clarified reserved terms

- 1.0

  - mime type changed to vnd.hyperglyph


planned changes
---------------


- 0.9 extensions frozen, http mapping frozen
	

- 1.0 compatibility promise
	1.1 should not break things

- 1.1 

	add paginated collection extension
	envelope: mixed; allow envelope on form inputs
	types for form inputs
	content_types on forms other than hyperglyph
	support for form-data/urlencoded 
	envelopes: url templates? 
	canonical html/json serialization,
	

TODO
====

fill out http mapping, more examples for status codes.
error handling/mapping

caching information/recommendations

pretty printing

worked example

references to fill in:

	safe rfc 2310
	utf-8 rfc
	datetime rfc, iso
	rfc of terms
	http rfc
	c99 hex floats
	mime types
	profile rel rfc
	url rfc


