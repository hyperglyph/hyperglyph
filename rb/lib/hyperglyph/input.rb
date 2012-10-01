module Hyperglyph
  class Input < Extension
    def name
      @attrs['name']
    end

    def default
      # should raise error
      @attrs['default']
    end
  end
end
