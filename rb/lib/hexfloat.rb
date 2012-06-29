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
    if s == 'nan'
      Float::NAN
    elsif s == "inf" or s =='infinity'
      Float::INFINITY
    elsif s == "-inf" or s =='-infinity'
      -Float::INFINITY
    else
      m = /(-?)0x([01]).([0-9abcdef]+)p(-?[0-9a-f]+)/.match s

      subnormal = (m[2] == "0")
      fractional = m[3].to_i(16)
      exponent = m[4].to_i()
      sign =  m[1] == "-" ? 128 :0

      exponent = subnormal ? 0 : [(exponent+1023) <<4].pack('n').bytes.to_a
      bits = [(fractional >> 32), (fractional & (2**32-1))].pack('NN').bytes.to_a
      bits[0..1] = [ sign | exponent[0], exponent[1] | bits[1] ]

      bits.pack('C*').unpack('G')[0]
    end
  end
end
class Float
  def to_hex
      if nan? or self == Float::INFINITY or self == -Float::INFINITY
        self.to_s
      else
        bits = [self].pack("G").bytes.to_a
        sign = (bits[0]&128) == 128? "-" : ""  
        exponent = 0 + ((bits[0]&127) <<4) +  ((bits[1]&240) >>4)
        fractional = sprintf "%x%02x%02x%02x%02x%02x%02x", bits[1]&15,*bits[2..7]
        normal = exponent > 0 ? 1 : 0
        if normal > 0
          exponent-=1023
        else # subnormal
          exponent = -1022 if fractional != "0"
        end
        "#{sign}0x#{normal}.#{fractional}p#{exponent}"
      end
  end
end


