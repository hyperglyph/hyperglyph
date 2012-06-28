require "glyph"
require "date"
require "stringio"
require "test/unit"

class EncodeTest < Test::Unit::TestCase
  def assert_encode (s)
      assert_equal(s, Glyph.load(Glyph.dump(s)))
  end
  def test_encode
    assert_encode(-1.729)
    assert_encode(1337)
    assert_encode("1.0")
    s=Set.new
    s.add("1")
    assert_encode({'a' =>1 , "b"=> 2})
    assert_encode([1,2,3,"123"])
    assert_encode(s)

    d= DateTime.now.new_offset(0)
    assert_encode(d)
    s = StringIO.new
    s.write("butts")
    assert_equal(s.string, Glyph.load(Glyph.dump(s)).string)
  end
end
