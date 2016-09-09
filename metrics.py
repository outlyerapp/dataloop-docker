import logging
import socket
import sys
import getopt
import time
import dl_lib

logger = logging.getLogger('METRICS')


def send_metrics(ctx):
    logger.debug("metrics")
    try:
        containers = dl_lib.get_containers(ctx)
        metrics = get_metrics(ctx, containers)
        publish_metrics(ctx, metrics)
    except Exception as ex:
        logger.error("metrics failed: %s" % ex, exc_info=True)


def get_metrics(ctx, containers):
    metrics = {}
    host_data = dl_lib.get_host_data(ctx)
    for container in containers:
        container_metrics = get_container_metrics(ctx, container, host_data)
        metrics.update(container_metrics)

    return metrics


def get_container_metrics(ctx, container, host):
    finger = dl_lib.hash_id(container['name'])

    stats = container['stats']
    last = stats[-1]

    metrics = {
        finger + '.base.count': 1,
        finger + '.base.load_1_min': last['cpu']['load_average'],
        finger + '.base.load_fractional': load_fractional(stats, host),
        finger + '.base.cpu': cpu_percent(stats, host),
        finger + '.base.memory': memory_percent(stats, host),
        finger + '.base.swap': 0,
        finger + '.base.net_upload': network_tx_kps(stats),
        finger + '.base.net_download': network_rx_kps(stats)
    }

    # send back everything else
    for group in ['network', 'diskio', 'memory', 'cpu']:
        group_metrics = dl_lib.flatten(last[group], key=group, path=finger)
        metrics.update(group_metrics)

    return metrics


def cpu_percent(stats, host):
    cores = host['num_cores']
    n_prev_stats = min(10, len(stats))
    # 60 samples in a list at 1 second interval. 59 being most recent.
    cpu_total_now = stats[-1]['cpu']['usage']['total']
    cpu_total_prev = stats[-n_prev_stats]['cpu']['usage']['total']

    # calculate the cpu difference over 10 seconds then calculate rate
    cpu_total_delta = cpu_total_now - cpu_total_prev
    cpu_total_rate = cpu_total_delta / n_prev_stats

    # total amount of cpu is number of billionths of a core
    total_compute_available = cores * 1000000000

    # now you can work out percentage cpu used per second
    return (float(cpu_total_rate) / float(total_compute_available)) * 100


def load_fractional(stats, host):
    return float(stats[-1]['cpu']['load_average']) / float(host['num_cores'])


def memory_percent(stats, host):
    memory = host['memory_capacity']
    # get most recent memory percentage
    return (float(stats[-1]['memory']['usage']) / float(memory)) * 100


def network_tx_kps(stats):
    n_prev_stats = min(10, len(stats))
    network_tx_now = stats[-1]['network']['tx_bytes']
    network_tx_prev = stats[-n_prev_stats]['network']['tx_bytes']
    return ((network_tx_now - network_tx_prev) / 1024) / n_prev_stats


def network_rx_kps(stats):
    n_prev_stats = min(10, len(stats))
    network_rx_now = stats[-1]['network']['rx_bytes']
    network_rx_prev = stats[-n_prev_stats]['network']['rx_bytes']
    return ((network_rx_now - network_rx_prev) / 1024) / n_prev_stats


def publish_metrics(ctx, metrics):
    sock = socket.socket()
    sock.connect((ctx["graphite_host"], ctx["graphite_port"]))

    for path, value in metrics.iteritems():
        if isinstance(value, int) or isinstance(value, float):
            message = "%s %s\n" % (path, value)
            sock.sendall(message)

    sock.close()


def main(argv):
    ctx = {
        "metric_interval": 30,
        "api_host": "https://agent.dataloop.io",
        "cadvisor_host": "http://127.0.0.1:8080",
        "graphite_host": "graphite.dataloop.io",
        "graphite_port": 2003
    }

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
            ctx['api_key'] = arg
        elif opt in ("-c", "--cadvisor"):
            ctx['cadvisor_host'] = arg
        elif opt in ("-u", "--apiurl"):
            ctx['api_host'] = arg
        elif opt in ("-s", "--graphiteserver"):
            ctx['graphite_host'] = arg
        elif opt in ("-p", "--graphiteport"):
            ctx['graphite_port'] = int(arg)

    while True:
        send_metrics(ctx)
        time.sleep(ctx['metric_interval'])


if __name__ == "__main__":
    main(sys.argv[1:])
