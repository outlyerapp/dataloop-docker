import getopt
import logging
import socket
import sys
import time
import grequests
import lib

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    stream=sys.stdout,
                    level=logging.INFO)

def ping(ctx):
    logger.debug("pinging")
    try:
        containers = lib.get_containers(ctx)
        container_ids = lib.get_container_ids(containers)
        ping_containers(ctx, container_ids)
    except Exception as ex:
        logger.error("register sync failed: %s" % ex, exc_info=True)


def ping_containers(ctx, container_ids):
    api_host = ctx['api_host']
    headers = lib.get_request_headers(ctx)
    host_mac = lib.get_host_mac(ctx)
    host_name = str(socket.gethostname())

    def create_request(id):
        details = {
            'mac': host_mac,
            'hostname': host_name,
            'tags': '',
            'os_name': 'docker',
            'os_version': '',
            'container_name': '',
            'proc_list': lib.get_processes(id),
            'ip': '',
            'interfaces': lib.get_network(id),
            'mode': 'solo',
            'name': str(id)
        }
        finger = lib.hash_id(id)
        url = "%s/api/agents/%s/ping" % (api_host, finger,)
        return grequests.post(url, json=details, headers=headers)

    reqs = map(create_request, container_ids)
    grequests.map(reqs)


def main(argv):
    ctx = {
        "ping_interval": 10,
        "api_host": "https://www.dataloop.io",
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