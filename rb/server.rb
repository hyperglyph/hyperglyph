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

  def self.queue
    Queue
  end
end

s = Service.new

queue = Service.queue

q = queue.new('bob')

puts q.instance_variables
puts "url for queue"
p s.url(queue)
puts "url for queue instance"
p s.url(q)

puts "url for queue method", q.method(:push)

p s.url(q.method(:push))

p s.GET

p s.call({'REQUEST_METHOD'=>'GET', 'PATH_INFO'=>'/'})

#Rack::Handler::WEBrick.run(Service.new, :Port => 12344)
