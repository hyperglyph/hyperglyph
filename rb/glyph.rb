require 'strscan'
require 'set'
require 'date'
require 'stringio'

class Integer
  def to_glyph
    "i#{self}\n"
  end
end

class String
  def to_glyph
    # assume in utf-8 wat
    "u#{self.length}\n#{self}"
  end
end

class StringIO
  def to_glyph
    # assume  bytestrings what
    "b#{self.string.length}\n#{self.string}"
  end
end

class Float
  def to_glyph
    "f#{Glyph.to_hexfloat(self)}\n"
  end
end

class Array
  def to_glyph
    "L#{map{|o| o.to_glyph }.join}E"
  end
end

class Set
  def to_glyph
    "S#{map{|o| o.to_glyph }.join}E"
  end
end

class Hash
  def to_glyph
    "D#{map{|k,v| [k.to_glyph, v.to_glyph]}.join}E"
  end
end

class TrueClass
  def to_glyph
    "T"
  end
end

class FalseClass
  def to_glyph
    "F"
  end
end

class NilClass
  def to_glyph
    "N"
  end
end

class DateTime
  def to_glyph
    "d#{strftime("%FT%TZ")}\n"
  end
end

# node, extension



module Glyph
  class DecodeError < StandardError
  end

  def self.dump(o)
    o.to_glyph
  end
  
  def self.load(str)
    scanner = StringScanner.new(str)
    return parse(scanner)
  end

  def self.parse(scanner)
    return case scanner.scan(/\w/)[-1]
    when ?T
      true
    when ?F
      false
    when ?N
      nil
    when ?i
      num = scanner.scan_until(/\n/)
      num.chop.to_i
    when ?d
      dt = scanner.scan_until(/\n/)
      DateTime.parse(dt)
    when ?f
      num = scanner.scan_until(/\n/)
      Glyph.from_hexfloat(num.chop)
    when ?u
      num = scanner.scan_until(/\n/).chop.to_i
      str = scanner.peek(num)
      scanner.pos+=num
      str
    when ?b
      num = scanner.scan_until(/\n/).chop.to_i
      str = scanner.peek(num)
      scanner.pos+=num
      StringIO.new(str)
    when ?D
      dict = {}
      until scanner.scan(/E/)

        key = parse(scanner)
        val = parse(scanner)
        dict[key]=val
      end
      dict

    when ?L
      lst = []
      until scanner.scan(/E/)
        lst.push(parse(scanner))
      end
      lst
    when ?S
      lst = Set.new
      until scanner.scan(/E/)
        lst.add(parse(scanner))
      end
      lst
    else
      raise Glyph::DecodeError, "baws"
    end
  end


  # i am a terrible programmer and I should be ashamed.
  #
  def self.from_hexfloat(s)
    # todo , nan, inf
    r = /(-?)0x([0-9a-fA-F]+)p(-?[0-9a-fA-F]+)/
    m = r.match s

    sign = m[1]
    mantissa = m[2].to_i(16)
    exponent = m[3].to_i(16)

    sign =  sign == "-" ? 128 :0
    exponent = (exponent+1023) <<4
    exponent = [exponent].pack('n')

    mantissa_t = mantissa >> 32;
    mantissa_b = mantissa & (2**32-1)

    mantissa = [mantissa_t, mantissa_b].pack('NN')

    bits = [
      sign | exponent[0],
      exponent[1] | mantissa[1],
      mantissa[2],
      mantissa[3],
      mantissa[4],
      mantissa[5],
      mantissa[6],
      mantissa[7],
    ].map {|x| x.chr}.join.unpack('G')[0]
  end

  def self.to_hexfloat(f)
      # todo nan, inf handling?
      bits = [f].pack("G")
      sign = -1*(bits[0]&128).to_i 
      sign = 1 if sign > -1 
      exponent = ((bits[0]&127)<<4) + ((bits[1]&240)>>4) - 1023
      mantissa = 1
      mantissa += (bits[1]&15)<<48
      mantissa += (bits[2]<<40)
      mantissa += (bits[3]<<32)
      mantissa += (bits[4]<<24) 
      mantissa += (bits[5]<<16) 
      mantissa += (bits[6]<<8)
      mantissa += bits[7]
      return "0x#{(sign*mantissa).to_s(16)}p#{exponent.to_s(16)}"
  end

end

p "abc".to_glyph
p 123.to_glyph
p [1,2,3].to_glyph

p "\n"; 

p Glyph.load("abc".to_glyph)
p Glyph.load(123.to_glyph)
p Glyph.load([1,2,3].to_glyph)
s=Set.new
s.add("1")
p Glyph.load([1,"2",true, false, nil, {"a" => 1}, s].to_glyph)

p Glyph.load(DateTime.now.to_glyph)
p Glyph.load((1.5).to_glyph)
s = StringIO.new
s.write("butts")
p Glyph.load(s.to_glyph).string


