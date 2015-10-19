#!/usr/bin/env python
import requests
from time import sleep
import sys
import os
import getopt
from docker.client import Client
from docker.utils import kwargs_from_env

API_KEY = ''  # You need to set this!
API_URL = 'https://www.dataloop.io'
CADVISOR = 'http://127.0.0.1:8080'
DEFAULT_TAGS = ['docker']

# Don't touch anything below this point. In fact don't even scroll down.

if os.path.exists('/rootfs/var/run/docker.sock'):
    docker_cli = Client(base_url='unix://rootfs/var/run/docker.sock', version='auto')
else:
    docker_cli = Client(**kwargs_from_env(assert_hostname=False))


def api_header():
    return {"Content-type": "application/json", "Authorization": "Bearer " + API_KEY}


def get_mac():
    return requests.get(CADVISOR + '/api/v1.3/machine').json()['system_uuid']


def add_tags(fingerprint, tag_list):
    data = {'names': ','.join(tag_list)}
    print 'Adding tags: %s to %s' % (','.join(tag_list), fingerprint)
    return requests.put(API_URL + "/api/agents/" + fingerprint + "/tags", json=data, headers=api_header())


def get_agent_tags():
    _resp = requests.get(API_URL + "/api/agents", headers=api_header())
    _agents = {}
    if _resp.status_code == 200:
        for l in _resp.json():
            if l['mac'] == get_mac():
                name = l['name']
                _agents[name] = {}
                _agents[name]['finger'] = l['id']
                _agents[name]['tags'] = l['tags']
    return _agents


def get_container_tags():
    _containers = {}
    _resp = requests.get(CADVISOR + '/api/v1.3/docker').json()
    for k, v in _resp.iteritems():
        _tags = []
        if 'system.slice' in v['name']:
            _name = (v['name'].replace('/system.slice/docker-', ''))
        else:
            _name = (v['name'].replace('/docker/', ''))
        for alias in v['aliases']:
            if alias != _name:
                _tags.append(alias)
        _containers[_name[:12]] = _tags
    return _containers


def get_container_image(container):
    return [docker_cli.inspect_container(container)['Config']['Image']]


def get_env_tags(container):
    env_tags = {}
    for env_var in docker_cli.inspect_container(container)['Config']['Env']:
        env_tags[env_var.split('=')[0]] = env_var.split('=')[1]
    return env_tags


def sync():
    try:
        agent_tags = get_agent_tags()
        container_tags = get_container_tags()
        tags = {}

        for agent, detail in agent_tags.iteritems():

            all_tags = []
            env_vars = get_env_tags(agent)
            env_vars_to_tag = ['ENV', 'APP_NAME']

            if len(container_tags) > 0:
                all_tags += container_tags[agent]

            if len(detail) > 0:
                all_tags += detail['tags']

            if len(DEFAULT_TAGS) > 0:
                all_tags += DEFAULT_TAGS

            all_tags += get_container_image(agent)

            for var in env_vars_to_tag:
                if var in env_vars:
                    all_tags += [env_vars[var]]

            diff = list(set(all_tags) - set(detail['tags']))
            tags[agent] = diff

        for agent, tag_list in tags.iteritems():
            if len(tag_list) > 0:
                add_tags(agent_tags[agent]['finger'], tag_list)

    except Exception as E:
        print "unable to sync tags!: %s" % E


def main(argv):
    global API_KEY, CADVISOR, API_URL

    try:
        opts, args = getopt.getopt(argv, "ha:c:u::", ["apikey=", "cadvisor=", "apiurl="])
    except getopt.GetoptError:
        print 'metrics.py -a <apikey> -c <cadvisor address:port> -u <dataloop address:port>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'metrics.py -a <apikey> -c <cadvisor address:port> -u <dataloop address:port>'
            sys.exit()
        elif opt in ("-a", "--apikey"):
            API_KEY = arg
        elif opt in ("-c", "--cadvisor"):
            CADVISOR = arg
        elif opt in ("-u", "--apiurl"):
            API_URL = arg

    print 'apikey:' + API_KEY
    print 'api url: ' + API_URL
    print 'cadvisor endpoint: ' + CADVISOR

    print "Container Tag running. Press ctrl+c to exit!"

    while True:

        sync()
        sleep(5)


if __name__ == "__main__":
    main(sys.argv[1:])
