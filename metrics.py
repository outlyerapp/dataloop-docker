#!/usr/bin/env python
import requests
import uuid
from time import sleep

API_KEY = ''
API = 'https://www.dataloop.io'
CADVISOR = 'http://192.168.99.100:8080'  # CAdvisor container URL. Change this if on Linux.


def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return str(uuid.getnode())


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


def get_metrics():
    pass


def send_metrics():
    pass


while True:
    # For each agent in Dataloop pull out the fingerprint


    # Get the metrics from CAdvisor


    # Prefix metrics with correct fingerprint


    # Send to Graphite port!


    sleep(5)    #  sleepy time