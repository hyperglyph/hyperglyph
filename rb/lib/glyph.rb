require 'strscan'
require 'set'
require 'date'
require 'stringio'
require 'net/http'
require 'uri'

# ruby1.9 or death!


# node, extension
module Glyph
  CONTENT_TYPE = "application/vnd.glyph"

  class FetchError < StandardError
  end
  class DecodeError < StandardError
  end

  class Node
    def initialize(name, attrs, content)
      @name = name
      @attrs = attrs
      @content = content
    end
    def method_missing(method, *args, &block)
        attr= @content[method.to_s]
        if attr and attr.respond_to?(:call)
          return attr.call(*args, &block)
        else
          super(method, *args, &block)
        end
    end

    def [](item)
      return @content[item]
    end
  end

  class Extension < Node
    def self.make(name, attrs, content)
      return case name
        when "form"
          return Form.new(name, attrs, content)
        when "link"
          return Link.new(name, attrs, content)
        when "embed"
          return Embed.new(name, attrs, content)
        else
          return Extension.new(name,attrs, content)
      end
    end

    def resolve url
      @attrs['url']=URI.join(url,@attrs['url']).to_s
    end

  end

  class Form < Extension
    def call(*args, &block)
      args = @attrs['values']? Hash[@attrs['values'].zip(args)] : {}
      ret = Glyph.fetch(@attrs['method'], @attrs['url'], args)
      if block
        block.call(ret)
      else
        ret
      end
    end
  end

  class Link < Extension
    def call(*args, &block)
      ret = Glyph.fetch(@attrs['method'], @attrs['url'], nil)
      if block
        block.call(ret)
      else
        ret
      end
    end
  end
    
  class Embed < Extension
    def call(*args, &block)
      if block
        block.call(@content)
      else
        @content
      end
    end
  end


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

  class Router
    def initialize()
      @routes = {}
      self.class.constants.each do |c|
        @routes[c.to_s] = self.class.const_get(c)
      end
    end
    def to_s
      "<#{self.class.to_s} #{@routes}>"
    end
      
    def call(env)
      path = env['PATH_INFO'].split
      method = env['REQUEST_METHOD']

      response = nil
      args = nil

      response = if path.empty?
        if method == 'GET'
          self.GET
        else
          self.POST(*args)
        end
      else

      end

      if response.nil?
        return [204, {}, []]
      else
        return [200, {'Content-Type'=>CONTENT_TYPE}, dump(response)]
      end
    end
    
    def GET
      content = {}
      @routes.each do |name, cls|
        content[name] = form(cls)
      end
      return Extension.make('resource', {'url'=>self}, content)
    end

    def POST

    end
    def url(resource)

    end

    def load(str)
      Glyph::load(obj)
    end

    def dump(obj)
      Glyph::dump(obj)
    end

    def form(obj) 
      if obj.class == Class
        args = obj.instance_method(:initialize).parameters
      elsif obj.class == Method
        args = obj.parameters
      end

      args=args.collect {|x| x[0] == :req and x[1]}
      Extension.make('form',{'method'=>'POST', 'url'=>obj}, args)
    end
  end

  def self.open(url) 
    fetch("GET", url, nil)
  end

  def self.fetch(method, url, data)
    uri = URI(url)
    req = case method.downcase
      when "post"
        path = (uri.query) ? "#{uri.path}?#{uri.query}" : uri.path
        Net::HTTP::Post.new(path)
      when "get"
        path = (uri.query) ? "#{uri.path}?#{uri.query}" : uri.path
        Net::HTTP::Get.new(path)
      else
        raise Glyph::FetchError, 'baws'
    end
    if method.downcase == "post"
      req.body = dump(data)
      req.content_type = CONTENT_TYPE
    end

    while true 
      res = Net::HTTP.start(uri.host, uri.port) do |s|
        s.request(req)
      end

      case res
        when Net::HTTPNoContent
          return nil
        when Net::HTTPSuccess
          scanner = StringScanner.new(res.body)
          return Glyph.parse(scanner, uri.to_s)
        when Net::HTTPRedirection
          uri = URI.join(uri.to_s, res['location'])
          path = (uri.query) ? "#{uri.path}?#{uri.query}" : uri.path
          req = Net::HTTP::Get.new(path)
        else
          raise Glyph::FetchError, res
      end
    end
  end

  def self.dump(o)
    if String === o
      u = o.encode('utf-8')
      "u#{u.bytesize}\n#{u}"
    elsif Integer === o
      "i#{o}\n"
    elsif StringIO === o
      "b#{o.string.length}\n#{o.string}"
    elsif Float === o
      "f#{Glyph.to_hexfloat(o)}\n"
    elsif Array === o
      "L#{o.map{|o| Glyph.dump(o) }.join}E"
    elsif Set === o
      "S#{o.map{|o| Glyph.dump(o) }.join}E"
    elsif Hash === o
      "D#{o.map{|k,v| [Glyph.dump(k), Glyph.dump(v)]}.join}E"
    elsif TrueClass === o
      "T"
    elsif FalseClass === o
      "F"
    elsif o.nil?
      "N"
    elsif DateTime === o
      "d#{o.strftime("%FT%T.%NZ")}\n"
    elsif Time === o
      "d#{o.strftime("%FT%T.%LZ")}\n"
    elsif Extention === o
      "H#{@name.to_glyph}#{@attrs.to_glyph}#{@content.to_glyph}"
    elsif Node === o
      "X#{@name.to_glyph}#{@attrs.to_glyph}#{@content.to_glyph}"
    elsif Resource === o
      raise EncodeError, 'unfinished'
    else
      raise EncodeError, 'unsupported'
    end
  end
  
  def self.load(str)
    scanner = StringScanner.new(str)
    return parse(scanner, "")
  end

  def self.parse(scanner, url)
    return case scanner.scan(/\w/)[-1]
    when ?T
      true
    when ?F
      false
    when ?N
      nil
    when ?i
      num = scanner.scan_until(/\n/)
      num.chop.to_i
    when ?d
      dt = scanner.scan_until(/\n/)
      DateTime.strptime(dt, "%FT%T.%L%Z")
    when ?f
      num = scanner.scan_until(/\n/)
      Glyph.from_hexfloat(num.chop)
    when ?u
      num = scanner.scan_until(/\n/).chop.to_i
      str = scanner.peek(num)
      scanner.pos+=num
      str
    when ?b
      num = scanner.scan_until(/\n/).chop.to_i
      str = scanner.peek(num)
      scanner.pos+=num
      StringIO.new(str)
    when ?D
      dict = {}
      until scanner.scan(/E/)

        key = parse(scanner, url)
        val = parse(scanner, url)
        dict[key]=val
      end
      dict

    when ?L
      lst = []
      until scanner.scan(/E/)
        lst.push(parse(scanner, url))
      end
      lst
    when ?S
      lst = Set.new
      until scanner.scan(/E/)
        lst.add(parse(scanner, url))
      end
      lst
    when ?X
      name = parse(scanner, url)
      attrs = parse(scanner, url)
      content = parse(scanner, url)
      n = Node.new(name, attrs, content)
      n
    when ?H
      name = parse(scanner, url)
      attrs = parse(scanner, url)
      content = parse(scanner, url)
      e = Extension.make(name, attrs, content)
      e.resolve(url)
      e
    else
      raise Glyph::DecodeError, "baws"
    end
  end


  # i am a terrible programmer and I should be ashamed.
  #
  def self.from_hexfloat(s)
    # todo , nan, inf
    r = /(-?)0x([0-9a-fA-F]+)p(-?[0-9a-fA-F]+)/
    m = r.match s

    sign = m[1]
    mantissa = m[2].to_i(16)
    exponent = m[3].to_i(16)

    sign =  sign == "-" ? 128 :0
    exponent = (exponent+1023) <<4
    exponent = [exponent].pack('n').bytes.to_a
    mantissa -=1

    mantissa_t = mantissa >> 32;
    mantissa_b = mantissa & (2**32-1)

    mantissa = [mantissa_t, mantissa_b].pack('NN').bytes.to_a

    bits = [
      sign | exponent[0], exponent[1] | mantissa[1], 
      mantissa[2], mantissa[3],
      mantissa[4], mantissa[5],
      mantissa[6], mantissa[7],
    ].map {|x| x.chr}.join.unpack('G')[0]
  end

  def self.to_hexfloat(f)
      # todo nan, inf handling?
      bits = [f].pack("G").bytes.to_a
      sign = (bits[0]&128).to_i 
      sign = sign == 128? "-" : ""  
      exponent = ((bits[0]&127)<<4) + ((bits[1]&240)>>4) - 1023
      mantissa = 1
      mantissa += (bits[1]&15)<<48
      mantissa += (bits[2]<<40)
      mantissa += (bits[3]<<32)
      mantissa += (bits[4]<<24) 
      mantissa += (bits[5]<<16) 
      mantissa += (bits[6]<<8)
      mantissa += bits[7]
      return "#{sign}0x#{mantissa.to_s(16)}p#{exponent.to_s(16)}"
  end
end





