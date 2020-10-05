default:
	@echo "an explicit target is required"

SOURCE_DIR_NAME=convert_ontology.py sdf/yaml2sdf.py
PRETTIER_FILES=.prettierrc.yaml *.md
YAML_FILES=.prettierrc.yaml

PRETTIER=prettier --ignore-path .gitignore

prettier-fix:
	$(PRETTIER) --write $(PRETTIER_FILES)

prettier-check:
	$(PRETTIER) --check $(PRETTIER_FILES)

lint:
	pylint $(SOURCE_DIR_NAME)

docstyle:
	pydocstyle --convention=google $(SOURCE_DIR_NAME)

mypy:
	mypy $(SOURCE_DIR_NAME)

flake8:
	flake8 $(SOURCE_DIR_NAME)

yamllint:
	yamllint --strict $(YAML_FILES)

black-fix:
	isort $(SOURCE_DIR_NAME)
	#black $(SOURCE_DIR_NAME)

black-check:
	isort --check $(SOURCE_DIR_NAME)
	#black --check $(SOURCE_DIR_NAME)

check: black-check flake8 mypy lint docstyle yamllint prettier-check

precommit: black-fix prettier-fix check

install:
	pip install -U pip setuptools wheel
	pip install -r requirements.txt -r requirements-dev.txt
