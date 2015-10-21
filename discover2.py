import getopt
import logging
import os
import socket
import threading
import sys
import time
import uuid
import grequests
import requests
from docker.client import Client
from docker.utils import kwargs_from_env

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    stream=sys.stdout,
                    level=logging.DEBUG)

register = []
uuid_hash = uuid.UUID('12345678123456781234567812345678')

if os.path.exists('/rootfs/var/run/docker.sock'):
    docker_cli = Client(base_url='unix://rootfs/var/run/docker.sock', version='auto')
else:
    docker_cli = Client(**kwargs_from_env(assert_hostname=False))

def get_request_headers(ctx):
    return {
        "Content-type": "application/json",
        "Authorization": "Bearer " + ctx['api_key']
    }


def get_host_mac(ctx):
    # #TEST code
    # return "macmacmacmac"
    cadvisor_url = ctx['cadvisor_host'] + '/api/v1.3/machine'
    return requests.get(cadvisor_url).json()['system_uuid']


def registration(ctx):
    while True:
        try:
            register_sync(ctx)
        except Exception as ex:
            logger.error("register sync failed: %s" % ex, exc_info=True)
        finally:
            time.sleep(ctx['register_interval'])


def register_sync(ctx):
    logger.info("register sync")

    agents = get_agents(ctx)
    agent_ids = get_agents_ids(agents)

    containers = get_containers(ctx)
    container_ids = get_container_ids(containers)
    logger.debug("containers: %s", container_ids)

    dead_containers = agent_ids - container_ids

    destroy_agents(ctx, dead_containers)


def get_containers(ctx):
    cadvisor_url = ctx['cadvisor_host'] + "/api/v1.3/docker"
    resp = requests.get(cadvisor_url).json()

    # # TEST containers
    # with open('../cadvisor.json') as conts:
    #     resp = json.load(conts)

    return resp.values()

def get_container_ids(containers):
    def get_id(c):
        if 'system.slice' in c['name']:
            return c['name'].replace('/system.slice/docker-', '')[:12]
        else:
            return c['name'].replace('/docker/', '')[:12]
    return set(map(get_id, containers))


def get_agents(ctx):
    agent_api = ctx['api_host'] + "/api/agents"

    resp = requests.get(agent_api, headers=get_request_headers(ctx))
    resp.raise_for_status()
    agents = resp.json()

    host_mac = get_host_mac(ctx)

    def filter_host(agent):
        return agent['mac'] == host_mac

    return filter(filter_host, agents)


def get_agents_ids(agents):
    def agent_name(agent):
        return agent['name']

    return set(map(agent_name, agents))

def destroy_agents(ctx, agent_ids):
    api_host = ctx['api_host']
    headers = get_request_headers(ctx)

    def create_request(id):
        finger = uuid.uuid5(uuid_hash, id)
        url = "%s/api/agents/%s/deregister" % (api_host, finger,)
        return grequests.post(url, headers=headers)

    reqs = map(create_request, agent_ids)
    grequests.map(reqs)


def ping(ctx):
    logger.debug("pinging")
    try:
        containers = get_containers(ctx)
        container_ids = get_container_ids(containers)
        ping_containers(ctx, container_ids)
    except Exception as ex:
        logger.error("register sync failed: %s" % ex, exc_info=True)


def ping_containers(ctx, container_ids):
    api_host = ctx['api_host']
    headers = get_request_headers(ctx)
    host_mac = get_host_mac(ctx)
    host_name = str(socket.gethostname())

    def create_request(id):
        details = {
            'mac': host_mac,
            'hostname': host_name,
            'tags': '',
            'os_name': 'docker',
            'os_version': '',
            'container_name': '',
            'proc_list': get_processes(id),
            'ip': '',
            'interfaces': get_network(id),
            'mode': 'solo',
            'name': str(id)
        }
        finger = uuid.uuid5(uuid_hash, id)
        url = "%s/api/agents/%s/ping" % (api_host, finger,)
        return grequests.post(url, json=details, headers=headers)

    reqs = map(create_request, container_ids)
    grequests.map(reqs)


def get_processes(container):
    process_list = []
    processes = docker_cli.top(container)['Processes']
    for process in processes:
        process_list.append(process[len(process) -1] + ':1')
    return process_list


def get_network(container):
    network_settings = docker_cli.inspect_container(container)['NetworkSettings']
    interface = [
        {
            'interface': 'eth0',
            'addresses': [
                {
                    'ips': [
                        network_settings['IPAddress']
                    ],
                    'family': 'AF_INET'
                }
            ]
        },
        {
            'interface': 'lo0',
            'addresses': [
                {
                    'ips': [
                        '127.0.0.1'
                    ],
                    'family': 'AF_INET'
                }
            ]
        }
    ]
    return interface


def main(argv):
    ctx = {
        "register_interval": 10,
        "ping_interval": 10,
        "api_host": "https://www.dataloop.io",
        "cadvisor_host": "http://127.0.0.1:8080"
    }

    try:
        opts, args = getopt.getopt(argv, "ha:c:u::", ["apikey=", "cadvisor=", "apiurl="])
    except getopt.GetoptError:
        print 'discover.py -a <apikey> -c <cadvisor address:port> -u <dataloop api address:port>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'discover.py -a <apikey> -c <cadvisor address:port> -u <dataloop address:port>'
            sys.exit()
        elif opt in ("-a", "--apikey"):
            ctx['api_key'] = arg
        elif opt in ("-c", "--cadvisor"):
            ctx['cadvisor_host'] = arg
        elif opt in ("-u", "--apiurl"):
            ctx['api_host'] = arg

    reg = threading.Thread(
        name="register",
        target=registration,
        args=(ctx,)
    )
    reg.start()

    while True:
        ping(ctx)
        time.sleep(ctx['ping_interval'])

if __name__ == "__main__":
    main(sys.argv[1:])
