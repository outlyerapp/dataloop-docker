#!/usr/bin/env python
import requests
import uuid
from time import sleep

API_KEY = ''  # You need to set this!
API = 'https://www.dataloop.io'
CADVISOR = 'http://192.168.99.100:8080'  # CAdvisor container URL. Change this if on Linux.

# Don't touch anything below this point. In fact don't even scroll down.


def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return str(uuid.getnode())


def get_agent_tags():
    # only get agents from dataloop that match the mac address of dl-dac container
    _resp = requests.get(API + "/api/agents", headers=api_header())
    _agents = {}
    if _resp.status_code == 200:
        for l in _resp.json():
            if l['mac'] == get_mac():
                name = l['name']
                _agents[name] = l['tags']
    return _agents


def get_container_tags():
    _containers = {}
    _tags = []
    try:
        _resp = requests.get(CADVISOR + '/api/v1.3/docker').json()
    except Exception as E:
        print "Failed to query containers: %s" % E
        return False

    for k, v in _resp.iteritems():
        _name = (v['name'].replace('/docker/', ''))
        for alias in v['aliases']:
            if alias != _name:
                _tags.append(alias)
        _containers[_name[:12]] = _tags
    return _containers


print "Container Tag running. Press ctrl+c to exit!"
while True:
    agent_tags = get_agent_tags()
    print "agent tags: %s" % agent_tags

    container_tags = get_container_tags()
    print "container tags: %s" % container_tags

    sleep(5)    #  sleepy time