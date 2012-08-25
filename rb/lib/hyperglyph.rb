require 'strscan'
require 'set'
require 'date'
require 'stringio'
require 'net/http'
require 'uri'

# ruby1.9 or death!

require 'hexfloat.rb'


# node, extension
module Hyperglyph
  CONTENT_TYPE = "application/vnd.glyph"

  class TimeDelta
    def initialize(period)
      @period = period
    end
  end

  class FetchError < StandardError
  end
  class DecodeError < StandardError
  end
  class EncodeError < StandardError
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
      @paths = {}
      self.class.constants.each do |c|
        name= c.to_s
        cls = self.class.const_get(c)
        @routes[name] = cls
        @paths[cls] = name
      end
    end
    def to_s
      "<#{self.class.to_s} #{@routes}>"
    end

    def dump_args(args)
      return URI.escape(dump(args))
    end

    def parse_args(str)
      return load(URI.unescape(str))
    end
    def load(str)
      Hyperglyph::load(str)
    end
    def dump(obj)
      Hyperglyph::dump(obj, self.method(:url), self.method(:inline))
    end
      
    def call(env)
      path = env['PATH_INFO'].split "/"
      method = env['HTTP_METHOD'] || env['REQUEST_METHOD']
      data = env['rack.input']

      response = nil
      path.shift

      data = data ? data.read : nil
  
      args = data.empty? ? nil: load(data).map(&:last) 
      if path.empty?
        obj = self
        methodname = method
      else
        cls = @routes[path.shift]
        methodname = path.shift ||  method

        query = env['QUERY_STRING']
        if cls.nil?
          raise StandardError, "unknown url"
        elsif not query.empty?
          query = parse_args(query)
          obj = cls.new(*query)
        else
          obj = cls
        end
      end
      #p "call #{obj} #{methodname} #{args}"
      response = obj.method(methodname).call(*args)
      #p "response #{response}"

      if response.nil?
        return [204, {}, []]
      else
        return [200, {'Content-Type'=>CONTENT_TYPE}, [dump(response)]]
      end
    end
    
    def url(resource)
      if resource === String
        return resource
      elsif Method === resource
        obj = resource.receiver
        cls = obj.class
        ins = []
        method = resource.name
        obj.instance_variables.each do |n|
          ins.push(obj.instance_variable_get(n))
        end
        ins = dump_args(ins)
      elsif Resource === resource
        cls=resource.class
        ins = []
        resource.instance_variables.each do |n|
          ins.push(resource.instance_variable_get(n))
        end
        method = ''
        ins = dump_args(ins)
      elsif resource.class == Class and resource <= Resource
        cls = resource
        ins = ''
        method = ''
      else
        raise EncodingError,"cant find url for #{resource}"
      end
      
      cls = @paths[cls]
      ins = ins.empty? ? '' : "?#{ins}"
      return "/#{cls}/#{method}#{ins}"
    end


    def inline(obj) 
      if Method === obj
        form(obj)
      elsif Resource === obj
        args = {}
        methods = obj.class.instance_methods - Resource.instance_methods
        methods.each do |m| 
          args[m] = form(obj.method(m))
        end
        obj.instance_variables.each do |n|
          args[n] = obj.instance_variable_get(n)
        end
        Extension.make('resource', {'url' => obj} , args)
      elsif obj.class == Class and obj <= Resource
        form(obj)
      else
        raise EncodingError,"cant inline #{obj}"
      end
    end

    def form(obj) 
      if obj.class == Class
        args = obj.instance_method(:initialize).parameters
      elsif obj.class == Method
        args = obj.parameters
      end

      args=args.collect {|x| x[0] == :req and x[1]}
      Extension.make('form',{'method'=>'POST', 'url'=>obj, 'values'=>args}, nil)
    end


    def GET
      # default contents 
      content = {}
      @routes.each do |name, cls|
        content[name] = form(cls)
      end
      return Extension.make('resource', {'url'=>"/"}, content)
    end

    def POST

    end

  end

  def self.get(url) 
    fetch("GET", url, nil)
  end

  def self.fetch(method, url, data)
    uri = URI(url)
      
    # todo handle adding Method: header
    req = case method.downcase
      when "post"
        path = (uri.query) ? "#{uri.path}?#{uri.query}" : uri.path
        Net::HTTP::Post.new(path)
      when "get"
        path = (uri.query) ? "#{uri.path}?#{uri.query}" : uri.path
        Net::HTTP::Get.new(path)
      else
        raise Hyperglyph::FetchError, 'baws'
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
          return Hyperglyph.parse(scanner, uri.to_s)
        when Net::HTTPRedirection
          uri = URI.join(uri.to_s, res['location'])
          path = (uri.query) ? "#{uri.path}?#{uri.query}" : uri.path
          req = Net::HTTP::Get.new(path)
        else
          raise Hyperglyph::FetchError, res
      end
    end
  end

  def self.blob(obj, content_type = 'application/octet-stream')
    Blob.new  obj, {'content-type' => content_type}
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

  class Extension < Node
    def self.make(name, attrs, content)
      return case name
        when "input"
          return Input.new(name, attrs, content)
        when "form"
          return Form.new(name, attrs, content)
        when "link"
          return Link.new(name, attrs, content)
        when "resource"
          return ExtResource.new(name, attrs, content)
        when "error"
          return ExtError.new(name, attrs, content)
          
        else
          return Extension.new(name,attrs, content)
      end
    end

  
    def resolve url
      @attrs['url']=URI.join(url,@attrs['url']).to_s
    end

  end

  class ExtError < Extension
  end

  class Blob 
    def initialize(content, attrs)
      @content = content
      @attrs = attrs
    end
    
    def fh
      @content
    end
    def content_type
      @attrs['content-type']
    end
  end

  class ExtResource < Extension
    def method_missing(method, *args, &block)
        attr= @content[method.to_s]
        if attr and attr.respond_to?(:call)
          r =  attr.call(*args, &block)
          return r
        else
          super(method, *args, &block)
        end
    end
  end
  class Form < Extension
    def call(*args, &block)
      names = @attrs['values'] ? @attrs['values'] : []
      a = args.clone

      data = names.map {|x|
        name = if Input === x
          x.name
        else
          x
        end
        val = if a.empty?
          x.default
        else
          a.pop
        end
        [name,val] 
      }
        
      data = Hash[data]
      ret = Hyperglyph.fetch(@attrs['method'], @attrs['url'], data)
      if block
        block.call(ret)
      else
        ret
      end
    end
  end

  class Input < Extension
    def name
      @attrs['name']
    end

    def default
      # should raise error
      @attrs['default']
    end
  end
  class Link < Extension
    def call(*args, &block)
      if @attrs['inline']
        if block
          block.call(@content)
        else
          @content
        end
      else
        ret = Hyperglyph.fetch(@attrs['method'], @attrs['url'])
        if block
          block.call(ret)
        else
          ret
        end
      end
    end
  end
    
  def self.dump(o, resolve=nil, inline=nil)
    blobs = []
    root = self.dump_one(o, resolve, inline, blobs)
    tail = self.dump_blobs(blobs)
    return "#{root}#{tail}"
  end

  def self.dump_one(o, resolve, inline, blobs)
    if Resource === o
      o = inline.call(o)
    end
    if Symbol === o
      u = o.to_s.encode('utf-8')
      if u.bytesize > 0
        "u#{u.bytesize}:#{u};"
      else 
        "u;"
      end
    elsif String === o
      u = o.encode('utf-8')
      if u.bytesize > 0
        "u#{u.bytesize}:#{u};"
      else 
        "u;"
      end
    elsif Integer === o
      "i#{o};"
    elsif StringIO === o
      b= o.string
      if b.length >0
        "b#{b.length}:#{b};"
      else 
        "b;"
      end
    elsif Float === o
      "f#{o.to_hex};"
    elsif Array === o
      "L#{o.map{|o| Hyperglyph.dump_one(o, resolve, inline, blobs) }.join};"
    elsif Set === o
      "S#{o.map{|o| Hyperglyph.dump_one(o, resolve, inline, blobs) }.join};"
    elsif Hash === o
      "O#{o.map{|k,v| [Hyperglyph.dump_one(k, resolve, inline, blobs), Hyperglyph.dump_one(v, resolve, inline, blobs)]}.join};"
    elsif TrueClass === o
      "T;"
    elsif FalseClass === o
      "F;"
    elsif o.nil?
      "N;"
    elsif DateTime === o
      "d#{o.strftime("%FT%T.%NZ")};"
    elsif TimeDelta === o
      "p#{o.iso_period};"
    elsif Time === o
      "d#{o.strftime("%FT%T.%LZ")};"
    elsif Blob === o
      bid = blobs.length
      blobs.push o.fh
      o.instance_eval {
        "B#{bid}:#{Hyperglyph.dump_one(@attrs, resolve, inline, blobs)};"
      }
    elsif Extension === o
      o.instance_eval {
        @attrs['url'] = resolve.call(@attrs['url']) if not String === @attrs['url']
        "X#{Hyperglyph.dump_one(@name, resolve, inline, blobs)}#{Hyperglyph.dump_one(@attrs, resolve, inline, blobs)}#{Hyperglyph.dump_one(@content,resolve, inline, blobs)};"
      }
    else
      raise EncodeError, "unsupported #{o}"
    end
  end

  def self.dump_blobs(blobs)
    blobs.each_with_index.map {|b,i|
      chunk = b.read
      if chunk.bytesize >0
        "c#{i}:#{chunk.bytesize}:#{chunk.to_s};c#{i};"
      else
        "c#{i};"
      end
    }.join
  end
  
  def self.load(str)
    scanner = StringScanner.new(str)
    return parse(scanner, nil)
  end

  def self.parse(scanner, url)
    blobs = {}
    res= self.parse_one(scanner, url, blobs)
    self.parse_blobs(scanner, blobs)
    res
  end

  def self.parse_one(scanner,url,blobs)
    s = scanner.scan(/[\w\n]/)[-1]
    return case s[-1]
    when ?T
      scanner.scan(/;/)
      true
    when ?F
      scanner.scan(/;/)
      false
    when ?N
      scanner.scan(/;/)
      nil
    when ?i
      num = scanner.scan_until(/;/)
      num.chop.to_i
    when ?d
      dt = scanner.scan_until(/;/)
      DateTime.strptime(dt, "%FT%T.%L%Z")
    when ?p
      per = scanner.scan_until(/;/)
      TimeDelta.iso_parse(per)
    when ?f
      num = scanner.scan_until(/;/)
      if num.index('x')
        num.chop.hex_to_f
      else
        num.chop.to_f
      end
    when ?u
      num = scanner.scan_until(/[:;]/)
      if num.end_with? ':'
        num = num.chop.to_i
        str = scanner.peek(num)
        scanner.pos+=num+1
        str
      else
        ''
      end
    when ?b
      num = scanner.scan_until(/[:;]/)
      if num.end_with? ':'
        num = num.chop.to_i
        str = scanner.peek(num)
        scanner.pos+=num+1
      else
        str = ''
      end
      StringIO.new(str)
    when ?D, ?O
      dict = {}
      until scanner.scan(/;/)
        key = parse_one(scanner, url, blobs)
        val = parse_one(scanner, url, blobs)
        dict[key]=val
      end
      dict

    when ?L
      lst = []
      until scanner.scan(/;/)
        lst.push(parse_one(scanner, url, blobs))
      end
      lst
    when ?S
      lst = Set.new
      until scanner.scan(/;/)
        lst.add(parse_one(scanner, url, blobs))
      end
      lst
    when ?X
      name = parse_one(scanner, url, blobs)
      attrs = parse_one(scanner, url, blobs)
      if attrs['url']
        attrs['url']=URI.join(url,attrs['url']).to_s
        content = parse_one(scanner, attrs['url'], blobs)
      else
        content = parse_one(scanner, url, blobs)
      end
      scanner.scan(/;/)
      e = Extension.make(name, attrs, content)
      e
    when ?B
      bid = scanner.scan_until(/:/).chop.to_i
      blobs[bid] = fd = StringIO.new
      attrs = parse_one(scanner, url, blobs)
      scanner.scan(/;/)
      blob(fd, attrs)
    else
      raise Hyperglyph::DecodeError, "baws #{s}"
    end
  end

  def self.parse_blobs(scanner, blobs)
    while not blobs.empty?
      s = scanner.scan(/[\w\n]/)[-1]
      case s[-1]
      when ?c
        num = scanner.scan_until(/[:;]/)
        term = num.end_with? ';'
        num = num.chop.to_i
        if term
          blobs[num].rewind
          blobs.delete num
        else
          len = scanner.scan_until(/:/).chop.to_i
          str = scanner.peek(len)
          blobs[num].write(str)
          scanner.pos+=len+1
        end
      else
        raise Hyperglyph::DecodeError, "baws #{s}"
      end
    end
  end

end


