#!/usr/bin/env python
import requests
import uuid
from time import sleep
import sys

API_KEY = ''
API = 'https://www.dataloop.io'
CADVISOR = 'http://192.168.99.100:8080'  # CAdvisor container URL. Change this if on Linux.


def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return str(uuid.getnode())

def flatten(structure, key="", path="", flattened=None):
    if flattened is None:
        flattened = {}

    if type(structure) not in (dict, list):
        flattened[((path + ".") if path else "") + key] = structure
    elif isinstance(structure, list):
        for i, item in enumerate(structure):
            flatten(item, "%d" % i, path + "." + key, flattened)
    else:
        for new_key, value in structure.items():
            flatten(value, new_key, path + "." + key, flattened)
    return flattened


def get_agents():
    # only get agents from dataloop that match the mac address of dl-dac container
    _resp = requests.get(API + "/api/agents", headers=api_header())
    agents = {}
    if _resp.status_code == 200:
        for l in _resp.json():
            print l['id']
            if l['mac'] == get_mac():
                name = l['name']
                agents[name] = l['id']
    return agents


def get_metrics():
    _containers = []
    _metrics = {}
    try:
        _resp = requests.get(CADVISOR + '/api/v1.3/docker').json()
    except Exception as E:
        print "Failed to query containers: %s" % E
        return False
    
    for k, v in _resp.iteritems():
	# print v['stats']
        ## TODO: v['stats'] contains all the metrics for this container
        _containers.append(v['name'].replace('/docker/', '')[:12])
        name = v['name'].replace('/docker/', '')[:12]
        _metrics[name] = v['stats']
    return _metrics


# send metrics to graphite
def send_msg(message, graphite_host, graphite_port):
    print "Sending message:\n%s" % message
    return # For testing

    try:
        sock = socket.socket()
    except socket.error, msg:
        print 'CRITICAL - Failed to create socket. Error code: %s - %s' % (msg[0], msg[1])
        sys.exit(2)
    try:
        sock.connect((graphite_host, int(graphite_port)))
    except Exception, e:
        print('CRITICAL - something is wrong with %s:%s. Exception is %s' % (graphite_host, graphite_port, e))
        sys.exit(2)
    sock.sendall(message)
    sock.close


    # metrics = []

    # for timestamp in times:
    #     index =  times.index(timestamp)
    #     # TODO some clever rollup for zeros
    #     metrics.append(("%s.%s %s%s %s") % (FINGER, PATH, values[index], UOM, int(timestamp) / 1000))

    # message =  '\n'.join(metrics)
    # send_msg(message, GRAPHITE_SERVER, PORT)


agents = get_agents()

metrics =  get_metrics()
# print metrics.keys()

flat_metrics = {}
for container,v in metrics.iteritems():
    # print container
    finger = agents[container]
    flat_metrics[container] = {}
    for a in v:
        # print a.keys()
        # print a['timestamp']
        for m in ['network', 'diskio', 'memory', 'cpu']:
            z = flatten(a[m], key=m, path=finger)
            flat_metrics[container].update(z)
            

for c,d in flat_metrics.iteritems():
    # print c
    for path, value in d.iteritems():
       print "%s %s" % ( path, value )
       # pass
		

sys.exit(0)

while True:
    # For each agent in Dataloop pull out the fingerprint


    # Get the metrics from CAdvisor


    # Prefix metrics with correct fingerprint


    # Send to Graphite port!


    sleep(5)    #  sleepy time
