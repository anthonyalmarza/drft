import coverage
import pytest


def main():
    cov = coverage.Coverage()
    cov.start()
    pytest.main()
    cov.stop()
    cov.save()
    cov.report()
