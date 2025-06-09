####################
# Setup tasks	   #
####################
install:
	pip install -r requirement.txt

setup_venv:
		python3.9 -m venv venv


setup: setup_venv
	(\
		. venv/bin/activate;\
		pip install -r requirements.txt;\
	)



####################
# Testing   	   #
####################
test:
	pytest  -vvv -x tests

lint:
	flake8 async.py boy.py app
	mypy --install-types --non-interactive async.py boy.py app

cover:
	coverage run --source=app,betonyou -m pytest --ignore=tests/integration --ignore=tests/legacy_integration -xv tests

coverage-report: cover
	coverage report -m --skip-empty

coverage-gutter: cover
	coverage html --skip-empty -d coverage
	coverage xml --skip-empty

bandit:
	bandit -r app boy.py

bandit-ci:
	bandit -r -ll -ii app boy.py

test-all: lint test bandit
