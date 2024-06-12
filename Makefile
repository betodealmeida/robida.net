all: check test

test:
	@if [ "$(filter test, $(MAKECMDGOALS))" = "test" ]; then \
		if [ "$(wordlist 2, $(words $(MAKECMDGOALS)), $(MAKECMDGOALS))" != "" ]; then \
			poetry run pytest --no-cov -vv $(wordlist 2, $(words $(MAKECMDGOALS)), $(MAKECMDGOALS)); \
		else \
			poetry run pytest --cov=src/robida --cov-report term-missing tests/; \
		fi \
	fi

# Prevents make from thinking test/path/to/file.py::test_name is a file target
%::
	@:

check:
	pre-commit run -a
