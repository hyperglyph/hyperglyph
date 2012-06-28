# i am a terrible programmer and I should be ashamed.
# todo nan, inf handling?
class String
  def hex_to_f
    s = self.downcase
    if s == 'nan'
      Float::NAN
    elsif s.start_with? "inf"
      Float::INFINITY
    elsif s.start_with? "-inf"
      -Float::INFINITY
    else
      m = /(-?)0x([01]).([0-9a-f]+)p(-?[0-9a-f]+)/.match s

      subnormal = (m[2] == "0")
      mantissa = m[3].to_i(16)
      exponent = m[4].to_i(16)
      sign =  m[1] == "-" ? 128 :0

      exponent = subnormal ? 0 : [(exponent+1023) <<4].pack('n').bytes.to_a
      bits = [(mantissa >> 32), (mantissa & (2**32-1))].pack('NN').bytes.to_a
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
        bits[0]&=127
        exponent = (bits[0..1].pack('C*').unpack('n')[0] >> 4) - 1023
        bits[0]&=0
        bits[1]&=15
        mantissa = bits.pack('C*').unpack('H*').join
        mantissa.slice! /^0+(?=[1-9]|0$)/

        if exponent > -1023
          "#{sign}0x1.#{mantissa}p#{exponent.to_s(16)}"
        elsif mantissa == "0"
          "#{sign}0x0.0p0"
        else
          "#{sign}0x0.#{mantissa}p-1022"
        end
      end
  end
end


