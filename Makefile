.DEFAULT_GOAL := help

###### Development commands

compile-requirements: ## Compile requirements files
	pip-compile requirements/base.in
	pip-compile requirements/dev.in

upgrade-requirements: ## Upgrade requirements files
	pip-compile --upgrade requirements/base.in
	pip-compile --upgrade requirements/dev.in

test: test-lint test-unit test-types test-format ## Run all tests

test-lint: ## Run linting tests
	pylint --errors-only --enable=unused-import,unused-argument lecture tests setup.py

test-unit: ## Run unit tests
	python -m unittest discover tests

test-types: ## Check types with mypy
	mypy --ignore-missing-imports --strict lecture tests

test-format: ## Check code formatting
	black --check lecture tests

format: ## Auto-format code with black
	black lecture tests setup.py

isort: ## Sort imports. This target is not mandatory because the output may be incompatible with black formatting. Provided for convenience purposes.
	isort --skip=templates lecture tests

examples: example-html example-olx ## Generate examples from the markdown file
.PHONY: examples

example-html: ## Generate HTML example from the markdown file
	lecture -v examples/course.md examples/course.html

example-olx: ## Generate OLX example from the markdown file
	rm -rf examples/olx/*
	lecture -v examples/course.md examples/olx/
	tar -czf examples/olx.tar.gz examples/olx

###### Additional commands

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
