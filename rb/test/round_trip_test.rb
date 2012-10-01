require "hyperglyph"
require "date"
require "stringio"
require "test/unit"

class EncodeTest < Test::Unit::TestCase
  def assert_encode(s)
    assert_equal(s, Hyperglyph.load(Hyperglyph.dump(s)))
  end

  def test_encode_negative_number
    assert_encode(-1.729)
  end

  def test_encode_positive_number
    assert_encode(+1.729)
  end

  def test_encode_negative_zero
    assert_encode(-0.0)
  end

  def test_encode_positive_zero
    assert_encode(+0.0)
  end

  def test_encode_exponent
    assert_encode(2.225073858507201e-308)
  end

  def test_encode_leet
    assert_encode(1337)
  end

  def test_encode_string
    assert_encode("1.0")
  end

  def test_encode_empty_string
    assert_encode("")
  end

  def test_encode_ascii_string
    skip("this was commented out, yo")
    assert_encode("".encode('ASCII-8BIT'))
  end

  def test_encode_set
    s = Set.new
    s.add("1")
    assert_encode(s)
  end

  def test_encode_hash
    assert_encode({'a' =>1 , "b"=> 2})
  end

  def test_encode_array
    assert_encode([1,2,3,"123"])
  end

  def test_encode_date
    d = DateTime.now.new_offset(0)
    assert_encode(d)
  end

  def test_encode_string_buffer
    s = StringIO.new
    s.write("butts")
    assert_equal(s.string, Hyperglyph.load(Hyperglyph.dump(s)).string)
  end

  def test_encode_io
    s = "Hello"
    b = Hyperglyph.blob(StringIO.new(s))
    b2 = Hyperglyph.load(Hyperglyph.dump(b))
    assert_equal(s, b2.fh.read)
  end
end
