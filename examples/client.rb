require "glyph"
s = Glyph.get(ARGV[0])
puts "out "
p s

puts ''

puts 'fetching queue'

q= s.Queue('butt')
puts 'got queue'
p q
puts ''

puts 'pushing'
q.push('butts')


p q.pop()
