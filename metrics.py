#!/usr/bin/env python
import requests
from time import sleep
import socket
import sys
import getopt

API_KEY = ''  # You need to set this!
API_URL = 'https://www.dataloop.io'
CADVISOR = 'http://127.0.0.1:8080'

GRAPHITE_SERVER = 'graphite.dataloop.io'
GRAPHITE_PORT = 2003


def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return requests.get(CADVISOR + '/api/v1.3/machine').json()['system_uuid']


def get_machine_data():
    return requests.get(CADVISOR + '/api/v1.3/machine').json()


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
    _resp = requests.get(API_URL + "/api/agents", headers=api_header())
    agents = {}
    if _resp.status_code == 200:
        for l in _resp.json():
            if l['mac'] == get_mac():
                name = l['name']
                agents[name] = l['id']
    return agents


def get_metrics():
    _metrics = {}
    _resp = requests.get(CADVISOR + '/api/v1.3/docker').json()
    for k, v in _resp.iteritems():
        if 'system.slice' in v['name']:
            name = (v['name'].replace('/system.slice/docker-', '')[:12])
        else:
            name = v['name'].replace('/docker/', '')[:12]

        _metrics[name] = v['stats']
    return _metrics


def send_msg(message):
    sock = socket.socket()
    sock.connect((GRAPHITE_SERVER, GRAPHITE_PORT))
    sock.sendall(message)
    sock.close()


def sync():
    try:
        machine_data = get_machine_data()
        cores = machine_data['num_cores']
        memory = machine_data['memory_capacity']
        agents = get_agents() or []
        metrics = get_metrics() or []

        flat_metrics = {}
        if len(agents) > 0 and len(metrics) > 0:
            for container, v in metrics.iteritems():

                finger = agents[container]
                flat_metrics[container] = {}

                samples = len(v) - 1

                # 60 samples in a list at 1 second interval. 59 being most recent.
                cpu_total_now = v[samples]['cpu']['usage']['total']
                cpu_total_prev = v[samples - 10]['cpu']['usage']['total']

                # calculate the cpu difference over 10 seconds then calculate rate
                cpu_total_delta = cpu_total_now - cpu_total_prev
                cpu_total_rate = cpu_total_delta / 10

                # total amount of cpu is number of billionths of a core
                total_compute_available = cores * 1000000000

                # now you can work out percentage cpu used per second
                cpu_percent = (float(cpu_total_rate) / float(total_compute_available)) * 100

                # get most recent memory percentage
                memory_percent = (float(v[samples]['memory']['usage']) / float(memory)) * 100

                # network stats

                network_tx_now = v[samples]['network']['tx_bytes']
                network_tx_prev = v[samples - 10]['network']['tx_bytes']
                network_tx_kps = ((network_tx_now - network_tx_prev) / 1024) / 10

                network_rx_now = v[samples]['network']['rx_bytes']
                network_rx_prev = v[samples - 10]['network']['rx_bytes']
                network_rx_kps = ((network_rx_now - network_rx_prev) / 1024) / 10

                # populate base metrics
                # load avg is current broken as per : https://github.com/google/cadvisor/issues/748
                base = {
                    finger + '.base.load_1_min': v[0]['cpu']['load_average'],
                    finger + '.base.cpu': cpu_percent,
                    finger + '.base.memory': memory_percent,
                    finger + '.base.swap': 0,
                    finger + '.base.net_upload': network_tx_kps,
                    finger + '.base.net_download': network_rx_kps
                }

                flat_metrics[container].update(base)

                # send back everything else
                for a in v:
                    for m in ['network', 'diskio', 'memory', 'cpu']:
                        z = flatten(a[m], key=m, path=finger)
                        flat_metrics[container].update(z)

            for c, d in flat_metrics.iteritems():
                for path, value in d.iteritems():
                    if isinstance(value, int) or isinstance(value, float):
                        message = "%s %s\n" % (path, value)
                        send_msg(message)

    except Exception as E:
        print "unable to sync metrics!: %s" % E


def main(argv):

    global API_KEY, CADVISOR, API_URL, GRAPHITE_SERVER, GRAPHITE_PORT

    try:
        opts, args = getopt.getopt(argv, "ha:c:u:s:p::", ["apikey=", "cadvisor=", "apiurl=", "graphiteserver=", "graphiteport="])
    except getopt.GetoptError:
        print 'metrics.py -a <apikey> -c <cadvisor address:port>  -u <dataloop address:port> -s <graphite server> -p <graphite port>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'metrics.py -a <apikey> -c <cadvisor address:port>  -u <dataloop address:port> -s <graphite server> -p <graphite port>'
            sys.exit()
        elif opt in ("-a", "--apikey"):
            API_KEY = arg
        elif opt in ("-c", "--cadvisor"):
            CADVISOR = arg
        elif opt in ("-u", "--apiurl"):
            API_URL = arg
        elif opt in ("-s", "--graphiteserver"):
            GRAPHITE_SERVER = arg
        elif opt in ("-p", "--graphiteport"):
            GRAPHITE_PORT = int(arg)

    print 'apikey: ' + API_KEY
    print 'api url: ' + API_URL
    print 'graphite server: ' + GRAPHITE_SERVER
    print 'graphite port: %d ' % GRAPHITE_PORT
    print 'cadvisor endpoint: ' + CADVISOR

    print "Container Metric Send running. Press ctrl+c to exit!"

    while True:
        sync()
        sleep(30)


if __name__ == "__main__":
    main(sys.argv[1:])
