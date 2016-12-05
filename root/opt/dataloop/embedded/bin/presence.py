import getopt
import logging
import socket
import sys
import time
import grequests
import dl_lib
import os

logger = logging.getLogger('PRESENCE')

os.environ['NO_PROXY'] = '127.0.0.1'

def ping(ctx):
    logger.debug("pinging")
    try:
        containers = dl_lib.get_containers(ctx)
        for container in containers:
            logger.debug( "found container: %s" % container['id'])
        container_paths = dl_lib.get_container_paths(containers)
        ping_containers(ctx, container_paths)
    except Exception as ex:
        logger.error("ping failed: %s" % ex, exc_info=True)

def exception_handler(request, exception):
    logger.info(request.url, "| request failed")


def ping_containers(ctx, container_paths):
    api_host = ctx['api_host']
    headers = dl_lib.get_request_headers(ctx)
    host_mac = dl_lib.get_host_mac(ctx)
    host_name = str(socket.gethostname())

    def create_request(path):
        id = dl_lib.get_container_id(path)
        details = {
            'mac': host_mac,
            'hostname': host_name,
            'os_name': 'docker',
            'os_version': '',
            'processes': dl_lib.get_processes(id),
            'container': '001',
            'interfaces': dl_lib.get_network(id),
            'mode': 'SOLO',
            'name': dl_lib.get_container_name(id)
        }
        finger = dl_lib.hash_id(path)
        url = "%s/agents/%s/ping" % (api_host, finger,)
        return grequests.post(url, json=details, headers=headers, timeout=2)

    reqs = map(create_request, container_paths)
    grequests.map(reqs, exception_handler=exception_handler)


def main(argv):
    ctx = {
        "ping_interval": 10,
        "api_host": "https://agent.dataloop.io",
        "cadvisor_host": "http://127.0.0.1:8080"
    }

    try:
        opts, args = getopt.getopt(argv, "ha:c:u::", ["apikey=", "cadvisor=", "apiurl="])
    except getopt.GetoptError:
        print 'presence.py -a <apikey> -c <cadvisor address:port> -u <dataloop api address:port>'
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
        ping(ctx)
        time.sleep(ctx['ping_interval'])

if __name__ == "__main__":
    main(sys.argv[1:])
