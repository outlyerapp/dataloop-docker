#!/usr/bin/env python
import requests
import uuid
import json
from time import sleep
from socket import gethostname
import sys,getopt

API_KEY = ''  # You need to set this!
EXCHANGE = 'https://agent.dataloop.io'
API = 'https://www.dataloop.io'
CADVISOR = 'http://127.0.0.1:8080'

# Don't touch anything below this point. In fact don't even scroll down.

def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return str(uuid.getnode())


def create_finger():
    return str(uuid.uuid4())


def agent_name_to_finger(name):
    try:
        _resp = requests.get(API + "/api/agents", headers=api_header()).json()
    except Exception as E:
        print "Failed to return agent details: %s" % E
        return "" # send an empty finger if we don't get one back
    for _agent in _resp:
        if _agent['name'] == name:
            return _agent['id']


def get_agents():
    # only get agents from dataloop that match the mac address of dl-dac container
    try:
        _resp = requests.get(API + "/api/agents", headers=api_header())
    except Exception as E:
        print "Failed to query agents: %s" % E
        return False

    # print "get_agents response: %s " % _resp.text

    agents = []
    if _resp.status_code == 200:
        for l in _resp.json():
            if l['mac'] == get_mac():
                agents.append(l['name'])

        return agents

    else:
        print "Bad response returning agent list: %s" % _resp.status_code
        return False


def get_agents_details(finger):
    _resp = requests.get(API + "/api/agents/" + finger, headers=api_header())
    if _resp.status_code == 200:
        return json.loads(_resp.text)
    else:
        print "failed to get agent details"


def register_agent(finger, data):
    try:
        return requests.post(EXCHANGE + '/agents/' + finger + '/register', json=data, headers=api_header())
    except Exception as E:
        print "Failed to register agent: %s" % E


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
        print "successfully registered %s" % _finger
    else:
        print "registration of %s failed with status code %d" % (_finger, resp.status_code)


def deregister_agent(finger):
    try:
        requests.post(EXCHANGE + '/agents/' + finger + '/deregister', headers=api_header())
    except Exception as E:
        print "Failed to deregister agent: %s" % E

    print "successfully deleted agent: %s" % finger
    return True


def get_containers():
    _containers = []
    try:
        _resp = requests.get(CADVISOR + '/api/v1.3/docker').json()
    except Exception as E:
        print "Failed to query containers: %s" % E
        return False

    for k, v in _resp.iteritems():
        _containers.append(v['name'].replace('/docker/', '')[:12])
    return _containers


def main(argv):
    global API_KEY, CADVISOR

    try:
       opts, args = getopt.getopt(argv,"ha:c::",["apikey=","cadvisor="])
    except getopt.GetoptError:
       print 'metrics.py -a <apikey> -c <cadvisor address:port>'
       sys.exit(2)
    for opt, arg in opts:
       if opt == '-h':
          print 'metrics.py -a <apikey> -c <cadvisor address:port>'
          sys.exit()
       elif opt in ("-a", "--apikey"):
          API_KEY = arg
       elif opt in ("-c", "--cadvisor"):
          CADVISOR = arg
    print 'apikey is "', API_KEY , '"'
    print 'cadvisor endpoint is "', CADVISOR, '"'

    print "Container Auto-Discovery running. Press ctrl+c to exit!"
    while True:

        agents = get_agents() or []
        print "dataloop agents: %s" % len(agents)

        containers = get_containers() or []
        print "cadvisor containers: %s" % len(containers)

        # add agents that don't exist in Dataloop
        if len(containers)>=0 and len(agents)>=0:
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


if __name__ == "__main__":
    main(sys.argv[1:])
