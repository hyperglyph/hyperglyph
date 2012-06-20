require "glyph"
s = Glyph.open(ARGV[0])
print "out "
p s

q= s.queue('butt')
p q

q.push('butts')
p q.pop()
