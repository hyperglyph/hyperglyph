require "glyph"
require "rack"
require "stringio"

$queues = {}

class Service < Glyph::Router

  class Queue < Glyph::Resource
    def initialize(name)
      p "init #{name}"
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

  def self.queue
    Queue
  end
end

s = Service.new

queue = Service.queue

q = queue.new('bob')
q.push('butts')
q.pop()

puts "s.call"

code, headers, data = s.call({'REQUEST_METHOD'=>'GET', 'PATH_INFO'=>'/'})
p Glyph.load(data)

#Rack::Handler::WEBrick.run(Service.new, :Port => 12344)
b = Glyph.dump([['name','butt']])
buf = StringIO.new()
buf.write(b)
buf.rewind
p "buf #{b}"
code, headers, data = s.call({'REQUEST_METHOD'=>'POST', 'PATH_INFO'=>'/Queue/', 'rack.input'=>buf})
p Glyph.load(data)
