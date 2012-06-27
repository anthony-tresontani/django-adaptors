.PHONY: test

test:
	python manage.py test --settings=test_settings

performance:
	echo "from performance import *; test_performance()"| python manage.py shell
