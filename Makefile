VENV = .venv
BIN = $(VENV)/bin
PYTHON = $(BIN)/python

all:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install black flake8
	$(BIN)/black .
	$(BIN)/flake8 --ignore E203,E501 kitten

publish: clean all
	$(PYTHON) -m pip install build twine
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*
	$(PYTHON) -m twine upload --username hoffa dist/*

clean:
	rm -rf $(VENV) dist
