require "hyperglyph"
require "rack"

$queues = {}

class Service < Hyperglyph::Router
  class Queue < Hyperglyph::Resource
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
