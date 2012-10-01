module Hyperglyph
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
end
