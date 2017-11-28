#!/usr/bin/env python3.6
import os
import logging
import aws_lambda_logging
import json
import uuid
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
import requests

aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))
logging.info(json.dumps({'message': 'initialising'}))
aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))


def get_correlation_id(body=None, payload=None, event=None):
    correlation_id = None
    if event:
        try:
            correlation_id = event['headers']['X-Amzn-Trace-Id'].split('=')[1]
        except:
            pass

    if body:
        try:
            correlation_id = body['trigger_id'][0]
        except:
            pass
    elif payload:
        try:
            correlation_id = payload['trigger_id']
        except:
            pass

    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    return correlation_id


def gocd_agent_list(gocd_base_url, headers, auth_user, auth_passwd):
    try:
        r = requests.get(url=gocd_base_url, headers=headers, auth=(auth_user, auth_passwd))
        r.raise_for_status()
        agents = r.json()['_embedded']['agents']
        logging.info(json.dumps({'message': 'listing agents', 'agents': [x['uuid'] for x in agents], 'reponse': r.status_code}))  # list comprehension filters response to only show agent UUIDs
    except:
        logging.exception(json.dumps({'message': 'listing agents', 'reponse': r.status_code}))
        raise
    return agents


def gocd_agent_disable(gocd_base_url, uri, headers, disable_patch, auth_user, auth_passwd):
    try:
        r = requests.patch(url=gocd_base_url + "/" + uri, headers=headers, data=json.dumps(disable_patch), auth=(auth_user, auth_passwd))
        r.raise_for_status()
        logging.info(json.dumps({'message': 'disable agent', 'agent': uri, 'reponse': r.status_code}))
        response = r.json()
    except:
        logging.exception(json.dumps({'message': 'disable agent', 'agent': uri, 'reponse': r.status_code}))
        raise
    return response


def gocd_agent_delete(gocd_base_url, uri, headers, auth_user, auth_passwd):
    try:
        r = requests.delete(url=gocd_base_url + "/" + uri, headers=headers, auth=(auth_user, auth_passwd))
        r.raise_for_status()
        logging.info(json.dumps({'message': 'removing agent', 'agent': uri, 'reponse': r.status_code}))
        response = r.json()
    except:
        logging.exception(json.dumps({'message': 'removing agent', 'agent': uri, 'reponse': r.status_code}))
        raise
    return response


def handler(event, context):
    correlation_id = get_correlation_id(event=event)
    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), correlation_id=correlation_id)

    gocd_base_url = os.environ['GOCD_URL']
    auth_user = os.environ['GOCD_USERNAME']
    auth_passwd = os.environ['GOCD_PASSWORD']
    headers = {
        'Accept': 'application/vnd.go.cd.v4+json',
        'Content-Type': 'application/json',
        'Correlation-Id': correlation_id
    }
    disable_patch = {
        'agent_config_state': 'Disabled'
    }

    gocd_list = gocd_agent_list(gocd_base_url, headers, auth_user, auth_passwd)

    logging.debug(json.dumps({'message': 'logging gocd_data', 'gocd_list': gocd_list}))

    for agent in gocd_list:
        if agent['hostname'] != 'MacMini' and (agent['agent_state'] == 'Missing' or agent['agent_state'] == 'LostContact') and agent['agent_config_state'] == 'Enabled':
            # func Disable
            gocd_agent_disable(gocd_base_url, agent['uuid'], headers, disable_patch, auth_user, auth_passwd)
            # func Delete
            gocd_agent_delete(gocd_base_url, agent['uuid'], headers, auth_user, auth_passwd)

        elif agent['hostname'] != 'MacMini' and agent['agent_config_state'] == 'Disabled':
            # func Delete
            gocd_agent_delete(gocd_base_url, agent['uuid'], headers, auth_user, auth_passwd)
        else:
            logging.info(json.dumps({'message': 'agent does not need to be disabled or deleted', 'uuid': agent['uuid'], 'state': agent['agent_state']}))


if __name__ == '__main__':
    handler({}, {})
