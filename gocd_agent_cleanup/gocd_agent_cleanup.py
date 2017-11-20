#!/usr/bin/env python3.6
import os
import logging
import aws_lambda_logging
import json
import uuid
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
import requests
from pprint import pprint


aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))
logging.info(json.dumps({'message': 'initialising'}))
aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'))

gocd_base_url = 'https://gocd.amaysim.net/go/api/agents'
auth_user = 'admin'
auth_passwd = 'xxx'
headers = {
    'Accept': 'application/vnd.go.cd.v4+json',
    'Content-Type': 'application/json',
    'Correlation-Id': correlation_id
}
disable_patch = {
    'agent_config_state': 'Disabled'
}


def handler(event, context):
    """Handler for gocd-agent-cleanup"""
    correlation_id = get_correlation_id(event=event)
    aws_lambda_logging.setup(level=os.environ.get('LOGLEVEL', 'INFO'), env=os.environ.get('ENV'), correlation_id=correlation_id)

    try:
        logging.debug(json.dumps({'message': 'logging event', 'status': 'success', 'event': event}))
    except:
        logging.exception(json.dumps({'message': 'logging event', 'status': 'failed'}))
        raise

    try:
        # do a thing
        main()
        thing = event
        logging.debug(json.dumps({'message': 'thing', 'status': 'success', 'thing': thing}))
    except:
        logging.exception(json.dumps({"message": "thing", "status": "failed"}))
        response = {
            "statusCode": 503,
            'headers': {
                'Content-Type': 'application/json',
            }
        }
        return response

    response = {
        "statusCode": 200,
        "body": json.dumps(thing),
        'headers': {
            'Content-Type': 'application/json',
        }
    }
    logging.info(json.dumps({'message': 'responding', 'response': response}))
    return response


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


def gocd_agent_list(uri):
    try:
        r = requests.get(url=gocd_base_url, headers=headers, auth=(auth_user, auth_passwd))
    except:
        print('Unknown Error')
    return r.json()


def gocd_agent_disable(uri):
    try:
        r = requests.patch(url=gocd_base_url + "/" + uri, headers=headers, data=json.dumps(disable_patch), auth=(auth_user, auth_passwd))
        # pprint (r.json())
    except:
        print('Unknown Error')
    return r.json()


def gocd_agent_delete(uri):
    try:
        r = requests.delete(url=gocd_base_url + "/" + uri, headers=headers, auth=(auth_user, auth_passwd))
        print(uri + " agent has been removed...")
    except:
        print('Unknown Error')
    return r.json()


def main():

    gocd_data = gocd_agent_list("")
    gocd_list = gocd_data['_embedded']['agents']

    # pprint (gocd_data)

    for agent in gocd_list:
        if agent['hostname'] != 'MacMini' and (agent['agent_state'] == 'Missing' or agent['agent_state'] == 'LostContact') and agent['agent_config_state'] == 'Enabled':
            print("Disabling " + agent['uuid'] + " it has status : " + agent['agent_state'])
            # func Disable
            gocd_agent_disable(agent['uuid'])
            # func Delete
            gocd_agent_delete(agent['uuid'])

        elif agent['hostname'] != 'MacMini' and agent['agent_config_state'] == 'Disabled':
            # print("Deleting " + agent['uuid'])
            # func Delete
            gocd_agent_delete(agent['uuid'])

if __name__ == '__main__':
    main()
