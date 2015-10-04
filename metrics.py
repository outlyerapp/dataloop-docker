#!/usr/bin/env python
import requests
import uuid
from time import sleep
import socket

API_KEY = ''
API = 'https://www.dataloop.io'
CADVISOR = 'http://192.168.99.100:8080'  # CAdvisor container URL. Change this if on Linux.
GRAPHITE_SERVER = 'graphite.dataloop.io'
GRAPHITE_PORT = 2003


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
        _containers.append(v['name'].replace('/docker/', '')[:12])
        name = v['name'].replace('/docker/', '')[:12]
        _metrics[name] = v['stats']
    return _metrics


# send metrics to graphite
def send_msg(message):
    # print "Sending message:\n%s" % message
    try:
        sock = socket.socket()
        sock.connect((GRAPHITE_SERVER, GRAPHITE_PORT))
        sock.sendall(message)
        sock.close()
    except Exception, e:
        print('CRITICAL - something is wrong with %s:%s. Exception is %s' % (GRAPHITE_SERVER, GRAPHITE_PORT, e))


print "Container Metric Send running. Press ctrl+c to exit!"
while True:
    agents = get_agents()
    metrics = get_metrics()

    flat_metrics = {}
    for container, v in metrics.iteritems():
        finger = agents[container]
        flat_metrics[container] = {}
        for a in v:
            for m in ['network', 'diskio', 'memory', 'cpu']:
                z = flatten(a[m], key=m, path=finger)
                flat_metrics[container].update(z)

    for c, d in flat_metrics.iteritems():
        for path, value in d.iteritems():
            if isinstance(value, int):
                message = "%s %s\n" % (path, value)
                send_msg(message)

    sleep(5)    #  sleepy time
