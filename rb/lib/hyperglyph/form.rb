module Hyperglyph
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
end
