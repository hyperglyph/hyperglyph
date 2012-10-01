module Hyperglyph
  class Extension < Node
    def self.make(name, attrs, content)
      return case name
        when "input"
          return Input.new(name, attrs, content)
        when "form"
          return Form.new(name, attrs, content)
        when "link"
          return Link.new(name, attrs, content)
        when "resource"
          return ExtResource.new(name, attrs, content)
        when "error"
          return ExtError.new(name, attrs, content)
          
        else
          return Extension.new(name,attrs, content)
      end
    end

  
    def resolve url
      @attrs['url']=URI.join(url,@attrs['url']).to_s
    end

  end
end
