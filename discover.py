import getopt
import logging
import sys
import time
import grequests
import requests
import lib

logger = logging.getLogger(__name__)


def registration(ctx):
    while True:
        try:
            register_sync(ctx)
        except Exception as ex:
            logger.error("register sync failed: %s" % ex, exc_info=True)
        finally:
            time.sleep(ctx['register_interval'])


def get_request_headers(ctx):
    return {
        "Content-type": "application/json",
        "Authorization": "Bearer " + ctx['api_key']
    }


def register_sync(ctx):
    logger.info("register sync")

    agents = get_agents(ctx)
    agent_ids = get_agents_ids(agents)

    containers = lib.get_containers(ctx)
    container_hashes = get_container_hashes(containers)
    logger.debug("containers: %s", container_hashes)

    dead_containers = agent_ids - container_hashes

    destroy_agents(ctx, dead_containers)


def get_container_hashes(containers):
    return set(map(lib.hash_id, lib.get_container_ids(containers)))


def get_agents(ctx):
    agent_api = ctx['api_host'] + "/api/agents"

    resp = requests.get(agent_api, headers=lib.get_request_headers(ctx))
    resp.raise_for_status()
    agents = resp.json()

    host_mac = lib.get_host_mac(ctx)

    def filter_host(agent):
        return agent['mac'] == host_mac

    return filter(filter_host, agents)


def get_agents_ids(agents):
    def agent_name(agent):
        return agent['id']

    return set(map(agent_name, agents))


def destroy_agents(ctx, agent_ids):
    api_host = ctx['api_host']
    headers = lib.get_request_headers(ctx)

    def create_request(id):
        url = "%s/api/agents/%s/deregister" % (api_host, id,)
        return grequests.post(url, headers=headers)

    reqs = map(create_request, agent_ids)
    grequests.map(reqs)


def main(argv):
    ctx = {
        "register_interval": 30,
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


    while True:
        registration(ctx)
        time.sleep(ctx['register_interval'])

if __name__ == "__main__":
    main(sys.argv[1:])
