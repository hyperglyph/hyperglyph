test: python_test ruby_test

python_test: py/
	python py/setup.py test

ruby_test: rb/
	cd rb && ruby tests.rb

