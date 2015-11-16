import getopt
import logging
import os
import sys
import time
import requests
import socket
from docker.client import Client
from docker.utils import kwargs_from_env
import dl_lib

logger = logging.getLogger(__name__)

if os.path.exists('/rootfs/var/run/docker.sock'):
    docker_cli = Client(base_url='unix://rootfs/var/run/docker.sock', version='auto')
else:
    docker_cli = Client(**kwargs_from_env(assert_hostname=False))


def ping_host(ctx):
    api_host = ctx['api_host']
    headers = dl_lib.get_request_headers(ctx)
    host_name = os.environ['HOST']
    host_mac = dl_lib.get_host_mac(ctx)
    finger = dl_lib.hash_id(host_mac)

    details = {
        'mac': host_mac,
        'hostname': host_name,
        'tags': '',
        'os_name': 'linux',
        'os_version': '',
        'container_name': '',
        'proc_list': '',
        'container_name': '',
        'ip': '',
        'interfaces': '',
        'mode': 'SOLO',
        'name': host_name
    }

    url = "%s/api/agents/%s/ping" % (api_host, finger,)
    print 'pinging: %s' % url
    return requests.post(url, json=details, headers=headers)


def send_host_metrics(ctx):
    sock = socket.socket()
    sock.connect((ctx["graphite_host"], ctx["graphite_port"]))

    host_mac = dl_lib.get_host_mac(ctx)
    finger = dl_lib.hash_id(host_mac)

    metrics = {
        finger + '.docker.containers': len(docker_cli.containers())
    }

    for path, value in metrics.iteritems():
        if isinstance(value, int) or isinstance(value, float):
            message = "%s %s\n" % (path, value)
            sock.sendall(message)

    sock.close()




def main(argv):
    ctx = {
        "ping_interval": 10,
        "api_host": "https://www.dataloop.io",
        "graphite_host": "graphite.dataloop.io",
        "graphite_port": 2003

    }

    try:
        opts, args = getopt.getopt(argv, "ha:c:u::", ["apikey=", "cadvisor=", "apiurl="])
    except getopt.GetoptError:
        print 'host.py -a <apikey> -c <cadvisor address:port> -u <dataloop api address:port>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'presence.py -a <apikey> -c <cadvisor address:port> -u <dataloop address:port>'
            sys.exit()
        elif opt in ("-a", "--apikey"):
            ctx['api_key'] = arg
        elif opt in ("-c", "--cadvisor"):
            ctx['cadvisor_host'] = arg
        elif opt in ("-u", "--apiurl"):
            ctx['api_host'] = arg

    while True:
        ping_host(ctx)
        send_host_metrics(ctx)
        time.sleep(ctx['ping_interval'])

if __name__ == "__main__":
    main(sys.argv[1:])
