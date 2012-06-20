require 'strscan'
require 'set'

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

class Float
  def to_glyph
    raise Glyph::EncodeError 'baws'
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


# bytestring b len \n <bytes>
# how to tell difference? maybe bytestrings are stringio
# float f <hex> \n

# set S..E

# datetime d <utc>Z \n

# true, false, none

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
    when ?f
      raise Glyph::DecodeError, 'baws'
    when ?u
      num = scanner.scan_until(/\n/).chop.to_i
      str = scanner.peek(num)
      scanner.pos+=num
      str
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

