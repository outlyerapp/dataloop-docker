import logging
import os
import uuid
from docker.client import Client
from docker.utils import kwargs_from_env
import sys
import requests

UUID_HASH = uuid.UUID('12345678123456781234567812345678')
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    stream=sys.stdout,
                    level=logging.INFO)

if os.path.exists('/rootfs/var/run/docker.sock'):
    docker_cli = Client(base_url='unix://rootfs/var/run/docker.sock', version='auto')
else:
    docker_cli = Client(**kwargs_from_env(assert_hostname=False))


def get_request_headers(ctx):
    return {
        "Content-type": "application/json",
        "Authorization": "Bearer " + ctx['api_key']
    }


def hash_id(id):
    return str(uuid.uuid5(UUID_HASH, id))


def get_containers(ctx):
    cadvisor_url = ctx['cadvisor_host'] + "/api/v1.3/docker"
    resp = requests.get(cadvisor_url).json()
    return resp.values()


def get_container(ctx, container):
    cadvisor_url = "%s/api/v1.3/%s" % (ctx['cadvisor_host'], container,)
    return requests.get(cadvisor_url).json()[container]


def get_container_paths(containers):
    def get_path(c):
        return c['name']

    return set(map(get_path, containers))

def get_container_env_vars(container):
    env_tags = {}
    for env_var in docker_cli.inspect_container(container)['Config']['Env']:
        env_tags[env_var.split('=')[0]] = env_var.split('=')[1]
    return env_tags


def get_container_id(path):
    if 'system.slice' in path:
        return path.replace('/system.slice/docker-', '')[:12]
    else:
        return path.replace('/docker/', '')[:12]


def get_host_mac(ctx):
    machine_url = ctx['cadvisor_host'] + '/api/v1.3/machine'
    return requests.get(machine_url).json()['system_uuid']


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
