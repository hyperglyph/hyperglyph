import glyph
import sys
s = glyph.get(sys.argv[1])

q= s.Queue(u'butt')
q.push(u'butts')
print  q.pop()
