import logging
import os
import uuid
from docker.client import Client
from docker.utils import kwargs_from_env
import sys
import requests
import re
import unicodedata
import socket

os.environ['NO_PROXY'] = '127.0.0.1'

UUID_HASH = uuid.UUID('12345678123456781234567812345678')
logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    stream=sys.stdout,
                    level=logging.WARNING)

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


def get_container_name(container):
    return docker_cli.inspect_container(container)['Name'][1:]


def container_real_host_name():
    with open('/rootfs/etc/hostname', 'r') as f:
        hostname = f.read()
    return hostname.strip()


def get_agents(ctx):
    host_mac = get_host_mac(ctx)
    agent_api = "%s/agents?mac=%s" % (ctx['api_host'], host_mac)
    try:
        resp = requests.get(agent_api, headers=get_request_headers(ctx), timeout=5)
        resp.raise_for_status()
        agents = resp.json()
    except:
        agents = ''
        logger.info("Failed to return agents by mac")

    def filter_host(agent):
        return agent['mac'] == host_mac

    return filter(filter_host, agents)


def get_agents_ids(agents):
    def agent_name(agent):
        return agent['id']

    return set(map(agent_name, agents))


def get_host_data(ctx):
    cadvisor_url = ctx['cadvisor_host'] + "/api/v1.3/machine"
    return requests.get(cadvisor_url).json()


def get_containers(ctx):
    cadvisor_url = ctx['cadvisor_host'] + "/api/v1.3/docker"
    resp = requests.get(cadvisor_url).json()
    # return resp.values()

    def filter_host_container(container):
        if container['id'][:12] != socket.gethostname():
            return container
        else:
            logger.debug("This container: %s" % container['id'])

    return filter(filter_host_container, resp.values())



def get_container(ctx, container):
    if container.startswith('/docker/'):
        cadvisor_url = "%s/api/v1.3/%s" % (ctx['cadvisor_host'], container,)
        return requests.get(cadvisor_url).json()[container]

    cadvisor_url = "%s/api/v1.3/containers/%s" % (ctx['cadvisor_host'], container,)
    return requests.get(cadvisor_url).json()


def get_container_paths(containers):
    def get_path(c):
        return c['name']

    return set(map(get_path, containers))


def get_container_env_vars(container):
    env_tags = {}
    if docker_cli.inspect_container(container)['Config']['Env'] is not None:
        for env_var in docker_cli.inspect_container(container)['Config']['Env']:
            env_tags[env_var.split('=')[0]] = env_var.split('=')[1]
    return env_tags


def get_container_labels(container):
    label_tags = {}
    if docker_cli.inspect_container(container)['Config']['Labels'] is not None:
        label_tags = docker_cli.inspect_container(container)['Config']['Labels']
    return label_tags


def get_container_id(path):
    if '/init.scope/system.slice/docker-' in path:
        return path.replace('/init.scope/system.slice/docker-', '')[:12]
    elif '/system.slice/docker-' in path:
        return path.replace('/system.slice/docker-', '')[:12]
    elif '/system.slice/docker.service/docker/' in path:
        return path.replace('/system.slice/docker.service/docker/', '')[:12]
    elif '/system.slice/var-lib-docker-containers-' in path:
        return path.replace('/system.slice/var-lib-docker-containers-', '')[:12]
    else:
        return path.replace('/docker/', '')[:12]


def get_host_mac(ctx):
    machine_url = ctx['cadvisor_host'] + '/api/v1.3/machine'
    return requests.get(machine_url).json()['system_uuid']


def get_processes(container):
    process_list = []
    processes = docker_cli.top(container)['Processes']
    for process in processes or []:
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


def slugify(value):
    _slugify_strip_re = re.compile(r'[^\w\/\\:]')
    _slugify_hyphenate_re = re.compile(r'[-\s\\\/]+')
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)
