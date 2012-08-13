import glyph
import sys
s = glyph.get(sys.argv[1])
print s
q= s.Queue(u'butt')
print q
q.push(u'butts')

print  q.pop()
