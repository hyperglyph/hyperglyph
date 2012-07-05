# i am a terrible programmer and I should be ashamed.

# hex notation for floating point numbers
# specified by c99, used in python, java
# http://docs.oracle.com/javase/6/docs/api/java/lang/Float.html#toHexString(float)

# floats are <sign bit> <exponent> <fractional>
# normal hex floats are (-)0x1.<fractional>p<exponent>
# fractional part in hex, exponent in decimal
# 0.0 is 0x0.0p0, -0.0 is -0x0.0p0
# subnormals are 0x0.<fractional>p-1022
# infinity is -inf/infinity

class String
  def hex_to_f
    s = self.downcase
    # handle the 'nan', 'inf', '-inf' cases for floats

    if s == 'nan'
      Float::NAN
    elsif s == "inf" or s =='infinity'
      Float::INFINITY
    elsif s == "-inf" or s =='-infinity'
      -Float::INFINITY
    else
      # a hex float, <sign> 0x <leading> . <fractional> p <exponent>
      # sign is +/-, leading is 0 or 1, fractional is hex digits, p is decimal
      # if leading is 1, a normal float
      # i.e 0.5 is +0x1.0000000000000p-1

      m = /(-?)0x([01]).([0-9abcdef]+)p([+\-]?[0-9a-f]+)/.match s

      # split out the parts 
      subnormal = (m[2] == "0")
      fractional = m[3].ljust(13,"0").to_i(16)
      exponent = m[4].to_i()
      sign =  m[1] == "-" ? 128 :0

      # double is 64 bits, 0 is sign,1-11 is exponent, 12-64 is fractional
      # in network byte order

      # if a subnormal, the exponent is stores as 0, else it's stored as exp+1023
      exponent = subnormal ? 0 : [(exponent+1023) <<4].pack('n').bytes.to_a
      # fractional is stored as is
      bits = [(fractional >> 32), (fractional & (2**32-1))].pack('NN').bytes.to_a
      bits[0..1] = [ sign | exponent[0], exponent[1] | bits[1] ]

      # transform the array of bytes in to a bytestring, then into a network order double 
      bits.pack('C*').unpack('G')[0]
    end
  end
end
class Float
  def to_hex
      if nan? or self == Float::INFINITY or self == -Float::INFINITY
        # these cases serialize as a string
        self.to_s
      else
        # hex representation
        bytes = [self].pack("G").bytes.to_a
        # transform floats into a array of bytes
        # sign is leading bit
        sign = (bytes[0]&128) == 128? "-" : ""  
        # exponent is bits 1 .. 11
        exponent = 0 + ((bytes[0]&127) <<4) +  ((bytes[1]&240) >>4)
        # fractional is remaining
        fractional = sprintf "%x%02x%02x%02x%02x%02x%02x", bytes[1]&15,*bytes[2..7]
        # strip trailing 0s from fractional part. 1.f0000 == 1.f, 
        fractional.slice! /(?<!^)0+$/
        if exponent > 0 # a normal float, so exponent is offset by 1023
          exponent-=1023  
          lead ="1"
        else # exponent is 0, so float is 0 or subnormal
          exponent = -1022 if fractional != "0"
          lead = "0"
        end
        "#{sign}0x#{lead}.#{fractional}p#{exponent}"
      end
  end
end


