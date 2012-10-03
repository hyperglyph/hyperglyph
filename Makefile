RUBY?=ruby
test: python_test ruby_test

python_test: py/
	cd py && python setup.py test

ruby_test: rb/
	rm -f rb/hyperglyph*.gem
	cd rb && gem build hyperglyph.gemspec
	gem install rb/hyperglyph*.gem
	${RUBY}  rb/tests.rb; gem uninstall hyperglyph

