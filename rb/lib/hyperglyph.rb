require 'strscan'
require 'set'
require 'date'
require 'stringio'
require 'net/http'
require 'uri'

require 'hyperglyph/hexfloat'
require 'hyperglyph/time_delta'
require 'hyperglyph/resource'
require 'hyperglyph/router'
require 'hyperglyph/node'
require 'hyperglyph/extension'
require 'hyperglyph/blob'
require 'hyperglyph/ext_resource'
require 'hyperglyph/form'
require 'hyperglyph/input'
require 'hyperglyph/link'

module Hyperglyph
  CONTENT_TYPE = "application/vnd.hyperglyph"

  FetchError = Class.new(StandardError)
  DecodeError = Class.new(StandardError)
  EncodeError = Class.new(StandardError)
  ExtError = Class.new(Extension)

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
