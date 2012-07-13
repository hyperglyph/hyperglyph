require 'strscan'
require 'set'
require 'date'
require 'stringio'
require 'net/http'
require 'uri'

# ruby1.9 or death!

require 'hexfloat.rb'


# node, extension
module Glyph
  CONTENT_TYPE = "application/vnd.glyph"

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
      Glyph::load(str)
    end
    def dump(obj)
      Glyph::dump(obj, self.method(:url), self.method(:inline))
    end
      
    def call(env)
      path = env['PATH_INFO'].split "/"
      method = env['REQUEST_METHOD']
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
          ins.push([n, obj.instance_variable_get(n)])
        end
        ins = dump_args(ins)
      elsif Resource === resource
        cls=resource.class
        ins = []
        resource.instance_variables.each do |n|
          ins.push([n,resource.instance_variable_get(n)])
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

  class BaseNode
    def initialize(name, attrs, content)
      @name = name
      @attrs = attrs
      @content = content
    end
  end


  class Node < BaseNode
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
        when "form"
          return Form.new(name, attrs, content)
        when "link"
          return Link.new(name, attrs, content)
        when "embed"
          return Embed.new(name, attrs, content)
        when "resource"
          return ExtResource.new(name, attrs, content)
        when "blob"
          return Blob.new(name, attrs, content)
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

  class Blob < Extension
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
      args = @attrs['values'] ? @attrs['values'].zip(args) : []
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


  def self.dump(o, resolve=nil, inline=nil)
    if Resource === o
      o = inline.call(o)
    end
    if Symbol === o
      u = o.to_s.encode('utf-8')
      "u#{u.bytesize}:#{u}"
    elsif String === o
      u = o.encode('utf-8')
      "u#{u.bytesize}:#{u}"
    elsif Integer === o
      "i#{o};"
    elsif StringIO === o
      "b#{o.string.length}:#{o.string}"
    elsif Float === o
      "f#{o.to_hex};"
    elsif Array === o
      "L#{o.map{|o| Glyph.dump(o, resolve, inline) }.join}E"
    elsif Set === o
      "S#{o.map{|o| Glyph.dump(o, resolve, inline) }.join}E"
    elsif Hash === o
      "D#{o.map{|k,v| [Glyph.dump(k, resolve, inline), Glyph.dump(v, resolve, inline)]}.join}E"
    elsif TrueClass === o
      "T"
    elsif FalseClass === o
      "F"
    elsif o.nil?
      "N"
    elsif DateTime === o
      "d#{o.strftime("%FT%T.%NZ")};"
    elsif Time === o
      "d#{o.strftime("%FT%T.%LZ")};"
    elsif Extension === o
      o.instance_eval {
        @attrs['url'] = resolve.call(@attrs['url']) if not String === @attrs['url']
        "H#{Glyph.dump(@name, resolve, inline)}#{Glyph.dump(@attrs, resolve, inline)}#{Glyph.dump(@content,resolve, inline)}"
      }
    elsif Node === o 
      o.instance_eval {
        "X#{Glyph.dump(@name, resolve, inline)}#{Glyph.dump(@attrs, resolve, inline)}#{Glyph.dump(@content,resolve, inline)}"
      }
    else
      raise EncodeError, "unsupported #{o}"
    end
  end
  
  def self.load(str)
    scanner = StringScanner.new(str)
    return parse(scanner, nil)
  end

  def self.parse(scanner, url)
    s = scanner.scan(/[\w\n]/)[-1]
    return case s[-1]
    when ?T
      true
    when ?F
      false
    when ?N
      nil
    when ?i
      num = scanner.scan_until(/;/)
      num.chop.to_i
    when ?d
      dt = scanner.scan_until(/;/)
      DateTime.strptime(dt, "%FT%T.%L%Z")
    when ?f
      num = scanner.scan_until(/;/)
      num.chop.hex_to_f
    when ?u
      num = scanner.scan_until(/:/).chop.to_i
      str = scanner.peek(num)
      scanner.pos+=num
      str
    when ?b
      num = scanner.scan_until(/:/).chop.to_i
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
      if url
        e.resolve(url)
      end
      e
    else
      raise Glyph::DecodeError, "baws #{s}"
    end
  end

end


