require "glyph"
require "rack"


class Service < Glyph::Router

  class Queue < Glyph::Resource
    def initialize(name)
      @name = name
    end

    def push

    end

    def pop

    end
  end
end

s = Service.new

p s.GET

p s.call({'REQUEST_METHOD'=>'GET', 'PATH_INFO'=>'/'})

#Rack::Handler::WEBrick.run(Service.new, :Port => 12344)
