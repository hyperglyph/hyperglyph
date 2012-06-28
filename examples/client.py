import glyph
import sys
s = glyph.get(sys.argv[1])
print "out "
print s

print 

print 'fetching queue'

q= s.Queue(u'butt')
print 'got queue'
print q
print ''

print 'pushing'
q.push(u'butts')


print  q.pop()
