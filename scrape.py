#!/usr/bin/env python
import os
import sys
import getopt
import time
import requests
import logging
import dl_lib
from prometheus_client.parser import text_string_to_metric_families

logger = logging.getLogger(__name__)

os.environ['NO_PROXY'] = '127.0.0.1'


def escape_string(s):
    escaped_string = ''
    special_chars = [',', '=', ' ', '"']
    for c in s:
        if c in special_chars:
            escaped_string += '\\' + c
        else:
            escaped_string += c
    return escaped_string


def is_digit(d):
    if d.lower() == 'nan':
        return False
    try:
        float(d)
    except ValueError:
        return False
    return True


def get_prometheus_metrics(prometheus_url):
    return requests.get(prometheus_url, timeout=5).content


def convert_prometheus_to_influxdb(prometheus_metrics):
    lines = []
    epoch = str(int(time.time() * 1000000000))
    for family in text_string_to_metric_families(prometheus_metrics):
        for sample in family.samples:
            tag_str = ''
            metric_str = sample[0]
            metric_parts = metric_str.split('_')
            metric = escape_string(metric_parts[0])
            value = str(sample[2])
            value_str = '_'.join(metric_parts[1:]) + "=" + value
            if is_digit(value) and not metric_str.startswith('#'):
                tags = sample[1]
                if tags:
                    for k, v in tags.iteritems():
                        tag_str += "," + k + "=" + escape_string(v)
                payload_line = metric + tag_str + " " + value_str + " " + epoch
                lines.append(payload_line)
    influxdb_metrics = '\n'.join(lines) + "\n"
    return influxdb_metrics


def post_influxdb_metrics(influxdb_url, influxdb_bucket, influxdb_metrics):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    return requests.post(influxdb_url, data=influxdb_metrics, headers=headers, auth=(influxdb_bucket, ''), timeout=5)


def scrape(ctx):
    logger.debug("scraping")
    try:
        containers = dl_lib.get_containers(ctx)
        container_paths = dl_lib.get_container_paths(containers)
        for container_path in container_paths:
            container = dl_lib.get_container(ctx, container_path)
            endpoint = prometheus_endpoint(container)
            bucket = dl_lib.hash_id(container_path)
            if endpoint:
                endpoint_metrics = get_prometheus_metrics(endpoint)
                influxdb_metrics = convert_prometheus_to_influxdb(endpoint_metrics)
                response = post_influxdb_metrics(
                    ctx["influxdb_url"],
                    bucket,
                    influxdb_metrics
                )
                if response.status_code != 200:
                    logger.error("status code: %s bucket: %s payload: %s" % (response.status_code, bucket, influxdb_metrics))
    except Exception as ex:
        logger.error("scraping failed: %s" % ex, exc_info=True)
    finally:
        time.sleep(ctx['scrape_interval'])



def prometheus_endpoint(container):
    container_id = dl_lib.get_container_id(container['name'])
    labels = dl_lib.get_container_labels(container_id)
    container_network = dl_lib.get_network(container_id)[0]['addresses'][0]['ips'][0]
    for k, v in labels.iteritems():
        if k.lower() == 'prometheus.port':
            return "http://%s:%d/metrics" % (container_network, int(v))


def main(argv):
    ctx = {
        "scrape_interval": 10,
        "influxdb_url": "http://influxdb.dataloop.io:8086/write?db=influxdb",
        "cadvisor_host": "http://127.0.0.1:8080"
    }

    try:
        opts, args = getopt.getopt(argv, "hu:c:", ["influxdb_url=", "cadvisor="])
    except getopt.GetoptError:
        print 'scrape.py -u <dataloop influxdb url e.g. http://influxdb.dataloop.io:8086/write?db=influxdb>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'scrape.py -u <http://influxdb.dataloop.io:8086/write?db=influxdb>'
            sys.exit()
        elif opt in ("-c", "--cadvisor"):
            ctx['cadvisor_host'] = arg
        elif opt in ("-u", "--influxdb_url"):
            ctx['influxdb_url'] = arg

    while True:
        scrape(ctx)
        time.sleep(ctx['scrape_interval'])


if __name__ == "__main__":
    main(sys.argv[1:])