module Hyperglyph
  class ExtResource < Extension
    def method_missing(method, *args, &block)
        attr= @content[method.to_s]
        if attr and attr.respond_to?(:call)
          r =  attr.call(*args, &block)
          return r
        else
          super(method, *args, &block)
        end
    end
  end
end
