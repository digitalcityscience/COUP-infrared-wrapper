
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

create-env:
	python3 -m venv $(VENV)

venv: create-env
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	$(VENV)/bin/pre-commit install
	cp .env.example .env

start:
	docker compose up --build

fmt:
	black ./user_api/ ./tests/
	isort ./user_api/ ./tests/

lint:
	black --check ./user_api/ ./tests/ 
	isort --check ./user_api/ ./tests/
	flake8 ./user_api/ ./tests/