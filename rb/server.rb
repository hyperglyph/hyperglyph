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

Rack::Handler::WEBrick.run(Service.new, :Port => 12344)


if nil 
  queue = Service.queue

  q = queue.new('bob')
  q.push('butts')
  q.pop()

  puts "s.call"

  code, headers, data = s.call({'REQUEST_METHOD'=>'GET', 'PATH_INFO'=>'/'})
  p Glyph.load(data)

  b = Glyph.dump([['name','butt']])
  buf = StringIO.new(b)
  buf.rewind
  code, headers, data = s.call({'REQUEST_METHOD'=>'POST', 'PATH_INFO'=>'/Queue/', 'rack.input'=>buf})
  q2 =  Glyph.load(data)

  url,query = q2['push'].instance_eval {@attrs['url']}.split '?'
  p "get #{url}"
  b = Glyph.dump([['a','butt']])
  buf = StringIO.new(b)
  buf.rewind
  code, headers, data = s.call({'REQUEST_METHOD'=>'POST', 'PATH_INFO'=>url, 'rack.input'=>buf,'QUERY_STRING'=>query})
  p Glyph.load(data)
end


