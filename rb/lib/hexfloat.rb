# i am a terrible programmer and I should be ashamed.
# todo nan, inf handling?
class Float
  def self.from_hex(s)
    r = /(-?)0x([01]).([0-9a-fA-F]+)p(-?[0-9a-fA-F]+)/
    m = r.match s

    sign = m[1]
    subnormal = (m[2] == "0")
    mantissa = m[3].to_i(16)
    exponent = m[4].to_i(16)

    sign =  sign == "-" ? 128 :0
    if subnormal
      exponent = 0
    else
      exponent = (exponent+1023) <<4
      exponent = [exponent].pack('n').bytes.to_a
    end


    mantissa_t = mantissa >> 32;
    mantissa_b = mantissa & (2**32-1)

    mantissa = [mantissa_t, mantissa_b].pack('NN').bytes.to_a

    bits = [
      sign | exponent[0], exponent[1] | mantissa[1], 
      mantissa[2], mantissa[3],
      mantissa[4], mantissa[5],
      mantissa[6], mantissa[7],
    ]
    bits = bits.pack('C*').unpack('G')[0]
  end

  def to_hex
      bits = [self].pack("G").bytes.to_a
      sign = (bits[0]&128).to_i 
      sign = sign == 128? "-" : ""  
      exponent = 0 
      exponent += (bits[0]&127)<<4 
      exponent += (bits[1]&240)>>4
      mantissa =0
      mantissa += (bits[1]&15)<<48
      mantissa += (bits[2]<<40)
      mantissa += (bits[3]<<32)
      mantissa += (bits[4]<<24) 
      mantissa += (bits[5]<<16) 
      mantissa += (bits[6]<<8)
      mantissa += bits[7]
      if exponent > 0
        exponent -=1023
        return "#{sign}0x1.#{mantissa.to_s(16)}p#{exponent.to_s(16)}"
      else
        if mantissa == 0
          return "#{sign}0x0.0p0"
        else
          return "#{sign}0x0.#{mantissa.to_s(16)}p-1022"
        end
      end
  end
end


