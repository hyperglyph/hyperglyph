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
-doubles/doubles
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

data types:
	considering ordered dictionaries, 

	dicts string only & unordered.? (easier interoperability)
	timezone support, time period support
	mime blocks? bytestrings with content-types/headers, offsets?? 
		akin to data urls?
	represents ad-hoc responses & inling

pagination in resources/collection types/ranges:
	with i.e 1-10 of n internally, 

schemas for forms:
	better form support - optional defaults.

caching/freshness:
	embed, resources have expiry information
	resources have method to refresh contents
	

specifics
---------

all datatypes are encoded into a byte string,
with some prefix ascii character to indicate 
the type

e.g
	u5:hello is a utf-8 string
	b5:world is a byte string 

strings!:
	utf-8 string -> u <byte len> : <utf-8 string>

	u5:hello
bytes!
	byte array -> b <byte len> :  <byte array>

	b5:hello

numbers:
	utc datetime -> d %Y-%m-%dT%H:%M:%S.%fZ ;
		note: currently only UTC times supported,
			  so all datetimes must end with Z

	d1970-01-01T00:00:00.000Z;

	num -> i <number> ;
		arbitrary precision whole number

	i123;

	double -> f <double in hex> ;
		double or double - the hex format is from
		c99 (-)0xMANTISSAp(-)EXPONENT

		i.e 0x1.ffp3, 0x0.0p0 -0x0.0p0

		normal doubles have mantissa of 0x1..
		subnormals have 0x0... (except 0)
		check java Double.toHexString / python double.hex
	   
		

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

hypermedia types/extensions: 
	ext -> H<name item><attr item><content item>
		like a node, but contains url, method, possibly form values.

	unlike nodes, these have special meaning inside of glyph, and 
	have defined behaviours


extensions
----------

currently the following extensions are defined:
	resource, link, form and embed


link:   

	name is "link"
	attr is a dict, containing the following keys: url, method
	content is None

form: 
  
	name is "form"
	attr is a dict, containing the following keys: url, method
		
	content is currently a list of names
	for the form to submit

	currently to submit a form, a k,v list is sent back
	as ordering is important.

embed:

	name is "embed"
	attr is a dict, containing the following keys: url, method
		
	content is the object that would be returned
	from fetching that link
	i.e if you followed the link & decoded it, what would you get back


resource
	name is "resource"
	attr is a dict, containing the following keys: url

	content is a dict of resource attributes
		often forms
		

all dictionary keys *should* be utf-8
			

whitespace/newlines
-------------------
parser SHOULD ignore whitespace when it doesn't change
semantics i.e

all same ::
	i 123 ;
	i123;
	i 123;
	i123 ;

includes whitespace between items

	i.e i123\r; and i123; are the same


unordered collections (dict/set)
--------------------------------
for the unordered collections, it is recommended
to order them in some way, such that the serializing
is consistent within the library, i.e

	dump(dict) equals dump(parse(dump(dict)))

but the ordering is ignored when reading.

example dumps:

>>> import glyph
>>> glyph.dump(u"hello, world")
'u12:hello, world'
>>> glyph.dump(b"hello, bytes")
'b12:hello, bytes'
>>> glyph.dump(1)
'i1;'
>>> glyph.dump(-1)
'i-1;'
>>> glyph.dump(1.0)
'f0x1.0000000000000p+0;'
>>> glyph.dump(-0.0)
'f-0x0.0p+0;'
>>> glyph.dump(2.225073858507201e-308)
'f0x0.fffffffffffffp-1022;'
>>> glyph.dump(double('nan'))
'fnan;'
>>> glyph.dump([1,2,3])
'Li1;i2;i3;E'
>>> glyph.dump(set([1,2,3]))
'Si1;i2;i3;E'
>>> glyph.dump({1:2,3:4})
'Di1;i2;i3;i4;E'
>>> glyph.dump(glyph.form('/url', values=['one', 'two'])
... )
'Hu4:formDu6:methodu4:POSTu3:urlu4:/urlu6:valuesLu3:oneu3:twoEEN'
>>> glyph.dump(glyph.form('/url', values=['one', 'two']))
'Hu4:formDu6:methodu4:POSTu3:urlu4:/urlu6:valuesLu3:oneu3:twoEEN'
>>> glyph.dump([True, False, None])
'LTFNE'


a note on doubles
-----------------

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


subnormals
----------

for subnormals and 0, the raw exponent is 0, and so the exponent is either

	0, if the fractional part is 0 
	-1022, if the fractional part is non 0

these are formatted with a leading 0, not 1
hex is 0x0.FRACTIONALpEXPONENT where FRACTIONAL is in hex, exponent in decimal::

	0.0f is  0x0.0p0
	0.0f is -0x0.0p0

a subnormal float like 2.225073858507201e-308
is in network byte order::

	offset:    0  8  16 32 40 48 56 64
	bytes:     00 0f ff ff ff ff ff ff

	raw_exponent is 0,
	fractional is 0xfffffffffffff

	hex is 0x0.fffffffffffffp-1022



changes
-------

using unicode everywhere instead of bytestrings
resource type, instead of node as default object type

