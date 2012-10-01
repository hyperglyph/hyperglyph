module Hyperglyph
  class Node
    def initialize(name, attrs, content)
      @name = name
      @attrs = attrs
      @content = content
    end

    def method_missing(method, *args, &block)
        attr= @content[method.to_s]
        if attr and attr.respond_to?(:call)
          r =  attr.call(*args, &block)
          return r
        else
          super(method, *args, &block)
        end
    end

    def [](item)
      return @content[item]
    end
  end
end
