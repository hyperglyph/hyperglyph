require "glyph"
require "rack"

$queues = {}

class Service < Glyph::Router
  class Queue < Glyph::Resource
    def initialize(name)
      @name = name
    end

    def push(a)
      if not $queues[@name]
        $queues[@name] = []
      end
      $queues[@name].push(a)
    end

    def pop
      $queues[@name].pop
    end
  end
end

Rack::Handler::WEBrick.run(Service.new, :Port => 12344)
