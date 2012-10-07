import hyperglyph
import sys
s = hyperglyph.get(sys.argv[1])
print s
q= s.Queue(u'butt')
print q
q.push(u'butts')

print  q.pop()
