# i am a terrible programmer and I should be ashamed.

require "scanf"

class String
  def hex_to_f
    case self.downcase
    when 'nan'
      Float::NAN
    when "inf", 'infinity'
      Float::INFINITY
    when "-inf", '-infinity'
      -Float::INFINITY
    else
      scanf("%a")[0]
    end
  end
end
class Float
  def to_hex
      if nan? or self == Float::INFINITY or self == -Float::INFINITY
        self.to_s
      else
        sprintf("%a", self)
      end
  end
end


