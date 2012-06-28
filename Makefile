RUBY?=ruby
test: python_test ruby_test

python_test: py/
	python py/setup.py test

ruby_test: rb/
	rm rb/glyph*.gem
	cd rb && gem build glyph.gemspec
	gem install rb/glyph*.gem
	${RUBY}  rb/tests.rb

