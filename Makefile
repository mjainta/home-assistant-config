MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-print-directory
MAKEFLAGS += --always-make

VENV_NAME?=venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate
PYTHON=${VENV_NAME}/bin/python
PIP=${VENV_NAME}/bin/pip


.PHONY: venv
dev:
	test -d $(VENV_NAME) || make create-venv

.PHONY: create-venv
create-venv:
	python3 -m venv $(VENV_NAME) && \
	${PIP} install -r requirements_all.txt

hass:
	hass -c ha-config

config-check:
	hass --script check_config -c ha-config
