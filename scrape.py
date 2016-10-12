#!/usr/bin/env python
import time
import requests
from prometheus_client.parser import text_string_to_metric_families

bucket = 'c67767a3-709e-5970-89fe-ad090e333687'

prom_data = requests.get('http://localhost:9100/metrics').content
influxdb_url = 'http://influxdb.dataloop.io:8086/write?db=node_exporter'
headers = {'Content-Type': 'application/x-www-form-urlencoded'}
epoch = str(int(time.time()*1000000000))
payload = ''

for family in text_string_to_metric_families(prom_data):
    for sample in family.samples:
        metric = str(sample[0]).lower()
        tags = sample[1]
        value = str(float(sample[2]))
        tag_string = ''
        if tags:
            for k, v in tags.iteritems():
                tag_string += "," + k + "=" + v
        # payload_line = "cpu,host=server01,region=us-west value=0.64 1434055562000000000\n"
        payload_line = metric + tag_string + ' value=' + value + " " + epoch + '\n'
        payload += payload_line

print payload
print requests.post(influxdb_url, data=payload, headers=headers, auth=(bucket, ''))

