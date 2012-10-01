module Hyperglyph
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
end
