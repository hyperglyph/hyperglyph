require "hyperglyph"
require "date"
require "stringio"
require "test/unit"

class EncodeTest < Test::Unit::TestCase
  def assert_encode (s)
      assert_equal(s, Hyperglyph.load(Hyperglyph.dump(s)))
  end
  def test_encode
    assert_encode(-1.729)
    assert_encode(+1.729)
    assert_encode(+0.0)
    assert_encode(-0.0)
    assert_encode(2.225073858507201e-308)
    assert_encode(1337)
    assert_encode("1.0")
    assert_encode("")
    #assert_encode("".encode('ASCII-8BIT'))
    s=Set.new
    s.add("1")
    assert_encode({'a' =>1 , "b"=> 2})
    assert_encode([1,2,3,"123"])
    assert_encode(s)

    d= DateTime.now.new_offset(0)
    assert_encode(d)
    s = StringIO.new
    s.write("butts")
    assert_equal(s.string, Hyperglyph.load(Hyperglyph.dump(s)).string)

    s= "Hello"
    b = Hyperglyph.blob(StringIO.new(s))
    b2 = Hyperglyph.load(Hyperglyph.dump(b))
    assert_equal(s, b2.fh.read)
  end
end
