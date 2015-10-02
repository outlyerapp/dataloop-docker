#!/usr/bin/env python
import requests
import uuid
import json
from time import sleep
from socket import gethostname

API_KEY = ''  # You need to set this!
EXCHANGE = 'https://agent.dataloop.io'
API = 'https://www.dataloop.io'
CADVISOR = 'http://192.168.99.100:8080'  # CAdvisor container URL. Change this if on Linux.

# Don't touch anything below this point. In fact don't even scroll down.

def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return str(uuid.getnode())


def create_finger():
    return str(uuid.uuid4())


def agent_name_to_finger(name):
    _resp = requests.get(API + "/api/agents", headers=api_header()).json()
    for _agent in _resp:
        if _agent['name'] == name:
            return _agent['id']


def get_agents():
    # only get agents from dataloop that match the mac address of dl-dac container
    _resp = requests.get(API + "/api/agents", headers=api_header())
    agents = []
    if _resp.status_code == 200:
        for l in _resp.json():
            if l['mac'] == get_mac():
                agents.append(l['name'])
        if len(agents) == 0:
            return []
        else:
            return agents
    else:
        return []


def get_agents_details(finger):
    _resp = requests.get(API + "/api/agents/" + finger, headers=api_header())
    if _resp.status_code == 200:
        return json.loads(_resp.text)
    else:
        print "failed to get agent details"


def register_agent(finger, data):
    return requests.post(EXCHANGE + '/agents/' + finger + '/register', json=data, headers=api_header())


def create_agent(container):
    # Generate a fingerprint
    _finger = create_finger()
    # print "generated fingerprint: %s" % _finger

    # Register an agent
    data = {
            'fingerprint': _finger,
            'tags': '',
            'name': container,
            'hostname': gethostname(),
            'mac': get_mac(),
            'os_name': 'docker',
            'os_version': '',
            'container': '',
            'processes': '',
            'interfaces': '',
            'mode': 'solo',
            'version': '',
            'interpreter': ''
    }

    resp = register_agent(_finger, data)
    if resp.status_code == 200:
        pass
        # print "successfully registered %s" % _finger
    else:
        print "registration of %s failed with status code %d" % (_finger, resp.status_code)


def deregister_agent(finger):
    return requests.post(EXCHANGE + '/agents/' + finger + '/deregister', headers=api_header())


def get_containers():
    _containers = []
    _resp = requests.get(CADVISOR + '/api/v1.3/docker').json()
    for k, v in _resp.iteritems():
        _containers.append(k.replace('/docker/', '')[:12])
    return _containers


print "Container Auto-Discovery running. Press ctrl+c to exit!"
while True:
    
    agents = get_agents()
    # print "dataloop agents: %s" % agents

    containers = get_containers()
    # print "cadvisor containers: %s" % containers

    # add agents that don't exist in Dataloop
    for container in containers:
        if container not in agents:
            print "adding container: %s" % container
            create_agent(container)


    # delete agents that don't exist as containers
    for agent in agents:
        if agent not in containers:
            print "deleting agent: %s" % agent
            finger = agent_name_to_finger(agent)
            deregister_agent(finger)

    sleep(5)  # have a little rest








