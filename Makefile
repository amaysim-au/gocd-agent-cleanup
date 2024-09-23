PACKAGE_DIR=package/package
ARTIFACT_NAME=package.zip
ARTIFACT_PATH=package/$(ARTIFACT_NAME)
ifdef AWS_ROLE
	ASSUME_REQUIRED?=assumeRole
endif
ifdef GO_PIPELINE_NAME
	ENV_RM_REQUIRED?=rm_env
endif


################
# Entry Points #
################
deps: .env
	docker compose run --rm serverless make _deps

build: .env _pullPythonLambda
	docker compose run --rm lambda-build make _build

deploy: .env $(ENV_RM_REQUIRED) $(ASSUME_REQUIRED)
	docker compose run --rm serverless make _deploy

logs: .env $(ENV_RM_REQUIRED) $(ASSUME_REQUIRED)
	docker compose run --rm serverless make _logs

smokeTest: .env $(ASSUME_REQUIRED)
	docker compose run --rm serverless make _smokeTest

remove: .env
	docker compose run --rm serverless make _deps _remove

styleTest: .env
	docker compose run --rm pep8 --ignore 'E501,E128' gocd_agent_cleanup/*.py

run: .env deps build _pullPythonLambda
	docker compose up --wait --detach lambda-run
	docker exec -it gocd-agent-cleanup-lambda-run-1 curl -f -s "http://127.0.0.1:8080/2015-03-31/functions/function/invocations" -d '' -v
	if [[ "$$?" -eq "0" ]]; then echo "Pass" && docker compose down; else echo "Fail" && docker compose down && false; fi

assumeRole: .env
	docker run --rm -e "AWS_ACCOUNT_ID" -e "AWS_ROLE" amaysim/aws:1.1.3 assume-role.sh >> .env

test: styleTest

shell: .env _pullPythonLambda
	docker compose run --rm lambda-build sh

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

venv:
	python3.11 -m venv --copies venv

_build: venv requirements.txt
	mkdir -p $(PACKAGE_DIR)
	sh -c 'source venv/bin/activate && pip install -r requirements.txt'
	cp -a venv/lib/python3.11/site-packages/. $(PACKAGE_DIR)/
	cp -a gocd_agent_cleanup/. $(PACKAGE_DIR)/
	@cd $(PACKAGE_DIR) && python -O -m compileall -q .
	cd $(PACKAGE_DIR) && zip -rq ../package .

$(ARTIFACT_PATH): .env _build

# Install node_modules for serverless plugins
_deps: node_modules.zip

node_modules.zip:
	yarn install --no-bin-links
	zip -rq node_modules.zip node_modules/

_deploy: node_modules.zip
	mkdir -p node_modules
	unzip -qo -d . node_modules.zip
	rm -fr .serverless
	sls deploy --verbose

_smokeTest:
	sls invoke -f handler

_logs:
	sls logs -f handler --startTime 5m -t

_remove:
	sls remove --verbose
	rm -fr .serverless

_clean:
	rm -fr node_modules.zip node_modules .serverless package .requirements venv/ run/ __pycache__/
	docker rmi -f gocd-agent-cleanup-lambda-build:latest
.PHONY: _deploy _remove _clean

_dockerLoginPublicECR: .env
	aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
.PHONY: _dockerLoginPublicECR

_pullPythonLambda: _dockerLoginPublicECR
	docker pull public.ecr.aws/lambda/python:3.11
.PHONY: _pullPythonLambda
