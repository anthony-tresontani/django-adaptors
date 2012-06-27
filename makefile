.PHONY: test

test:
	./runtests.py

performance:
	echo "from performance import *; test_performance()"| python manage.py shell
