#!/usr/bin/env python
import requests
from prometheus_client.parser import text_string_to_metric_families
from influxdb import InfluxDBClient, exceptions
from datetime import datetime

current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
prom_data = requests.get('http://localhost:9100/metrics').content
influxdb_client = InfluxDBClient('influxdb.dataloop.io', 8086, 'c67767a3-709e-5970-89fe-ad090e333687', '', 'node_exporter')

for family in text_string_to_metric_families(prom_data):
    for sample in family.samples:
        json_body = [
            {
                "measurement": sample[0],
                "tags": sample[1],
                "time": current_time,
                "fields": {
                    "value": sample[2]
                }
            }
        ]
        try:
            print influxdb_client.write_points(json_body)
        except exceptions.InfluxDBClientError, c:
            if c.code == 200:
                continue
        except exceptions.InfluxDBServerError, s:
            continue
