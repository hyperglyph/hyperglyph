RUBY?=ruby
test: python_test ruby_test

python_test: py/
	python py/setup.py test

ruby_test: rb/
	${RUBY} -Irb rb/tests.rb

