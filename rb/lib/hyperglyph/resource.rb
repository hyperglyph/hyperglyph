module Hyperglyph
  class Resource
    def GET
        return self
    end

    def POST
    end

    def self.GET
    end
    
    def self.POST(*args)
      return new(*args)
    end

  end
end
