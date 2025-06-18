#!/bin/sh -xe
ruff check ./
mypy ./
pytest ./tests
sphinx-build -W -b html -d ./dist/docs/trees ./docs ./dist/docs/html
