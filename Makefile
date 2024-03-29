PACKAGE_DIR=package/package
ARTIFACT_NAME=package.zip
ARTIFACT_PATH=package/$(ARTIFACT_NAME)
ifdef DOTENV
	DOTENV_TARGET=dotenv
else
	DOTENV_TARGET=.env
endif
ifdef AWS_ROLE
	ASSUME_REQUIRED?=assumeRole
endif
ifdef GO_PIPELINE_NAME
	ENV_RM_REQUIRED?=rm_env
else
	USER_SETTINGS=--user $(shell id -u):$(shell id -g)
endif


################
# Entry Points #
################
deps: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps

build: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm lambda-build make _build

deploy: $(ENV_RM_REQUIRED) $(DOTENV_TARGET) $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deploy

logs: $(ENV_RM_REQUIRED) $(DOTENV_TARGET) $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm serverless make _logs

unitTest: $(ASSUME_REQUIRED) $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm lambda gocd_agent_cleanup.unit_test

smokeTest: $(DOTENV_TARGET) $(ASSUME_REQUIRED)
	docker-compose run $(USER_SETTINGS) --rm serverless make _smokeTest

remove: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm serverless make _deps _remove

styleTest: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm pep8 --ignore 'E501,E128' gocd_agent_cleanup/*.py

run: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm lambda gocd_agent_cleanup.handler

assumeRole: $(DOTENV_TARGET)
	docker run --rm -e "AWS_ACCOUNT_ID" -e "AWS_ROLE" amaysim/aws:1.1.3 assume-role.sh >> .env

test: $(DOTENV_TARGET) styleTest

shell: $(DOTENV_TARGET)
	docker-compose run $(USER_SETTINGS) --rm lambda-build sh

##########
# Others #
##########

# Removes the .env file before each deploy to force regeneration without cleaning the whole environment
rm_env:
	rm -f .env
.PHONY: rm_env

# Create .env based on .env.template if .env does not exist
.env:
	@echo "Create .env with .env.template"
	cp .env.template .env

# Create/Overwrite .env with $(DOTENV)
dotenv:
	@echo "Overwrite .env with $(DOTENV)"
	cp $(DOTENV) .env

$(DOTENV):
	$(info overwriting .env file with $(DOTENV))
	cp $(DOTENV) .env
.PHONY: $(DOTENV)

venv:
	virtualenv --python=python3.8 --always-copy venv

_build: venv requirements.txt
	mkdir -p $(PACKAGE_DIR)
	sh -c 'source venv/bin/activate && pip install -r requirements.txt'
	cp -a venv/lib/python3.8/site-packages/. $(PACKAGE_DIR)/
	cp -a gocd_agent_cleanup/. $(PACKAGE_DIR)/
	@cd $(PACKAGE_DIR) && python -O -m compileall -q .
	cd $(PACKAGE_DIR) && zip -rq ../package .

$(ARTIFACT_PATH): $(DOTENV_TARGET) _build

# Install node_modules for serverless plugins
_deps: node_modules.zip

node_modules.zip:
	yarn install --no-bin-links
	zip -rq node_modules.zip node_modules/

_deploy: node_modules.zip
	mkdir -p node_modules
	unzip -qo -d . node_modules.zip
	rm -fr .serverless
	sls deploy -v

_smokeTest:
	sls invoke -f handler

_logs:
	sls logs -f handler --startTime 5m -t

_remove:
	sls remove -v
	rm -fr .serverless

_clean:
	rm -fr node_modules.zip node_modules .serverless package .requirements venv/ run/ __pycache__/
.PHONY: _deploy _remove _clean
