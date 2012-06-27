#!/usr/bin/env python
import sys
from optparse import OptionParser

from django.conf import settings

if not settings.configured:
    settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                }
            },
            INSTALLED_APPS=[
                'tests.test_app',
            ],
            NOSE_ARGS=['-s'],
        )

from django_nose import NoseTestSuiteRunner


def run_tests(nose_options, test_args):
    if not test_args:
        test_args = ['tests']
    test_runner = NoseTestSuiteRunner(verbosity=nose_options.verbosity)
    failures = test_runner.run_tests(test_args)
    sys.exit(failures)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-v', '--verbose', dest='verbosity', default=1, type=int)
    (options, args) = parser.parse_args()
    
    run_tests(options, args)
