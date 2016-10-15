#!/usr/bin/env python
import time
import requests
from prometheus_client.parser import text_string_to_metric_families


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
    try:
        float(d)
    except ValueError:
        return False
    return True


def get_prometheus_metrics(prometheus_url):
    return requests.get(prometheus_url).content


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
    return requests.post(influxdb_url, data=influxdb_metrics, headers=headers, auth=(influxdb_bucket, ''))



# get, convert, post
node_exporter_metrics = get_prometheus_metrics('http://localhost:9100/metrics')
influxdb_metrics = convert_prometheus_to_influxdb(node_exporter_metrics)
influxdb_response = post_influxdb_metrics(
    'http://influxdb.dataloop.io:8086/write?db=influxdb',
    'c67767a3-709e-5970-89fe-ad090e333687',
    influxdb_metrics
)
print influxdb_response