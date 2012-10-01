Gem::Specification.new do |s|
  s.name        = 'hyperglyph'
  s.version     = '0.9.0'
  s.date        = '2012-08-12'
  s.summary     = "hyperglyph"
  s.description = "duck typed ipc over http"
  s.authors     = ["tef"]
  s.email       = 'tef@hyperglyph.twentygototen.org'
  s.homepage         = 'http://hyperglyph.net/'
  s.files         = `git ls-files`.split("\n")
  s.test_files    = `git ls-files -- test/*`.split("\n")
end
