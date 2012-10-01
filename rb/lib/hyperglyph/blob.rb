module Hyperglyph
  class Blob 
    def initialize(content, attrs)
      @content = content
      @attrs = attrs
    end
    
    def fh
      @content
    end
    def content_type
      @attrs['content-type']
    end
  end
end
