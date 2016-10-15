# Dataloop Docker Autodiscovery Container

Run a single copy of this container on each of your Docker hosts.

This container includes a full Dataloop agent which can be used to run plugins, a copy of CAdvisor which is used to
collect Operating System metrics and some automation scripts that create virtual agents in Dataloop for all containers
on the host.

CAdvisor returns approximately 100 individual metrics per container. More metrics are returned for the host that the
containers run on.

This container was also designed to automatically scrape Prometheus endpoints. Either from 3rd party exporters for
services like RabbitMQ, Mongo and Nginx. Or from your own custom instrumented code running in containers.

To run this container:

```
API_KEY=<<Dataloop API Key>>
sudo docker run -d -e API_KEY=${API_KEY} \
--name=$HOSTNAME \
--volume=/:/rootfs:ro \
--volume=/var/run:/var/run:rw \
--volume=/sys:/sys:ro \
--volume=/var/lib/docker/:/var/lib/docker:ro \
dataloop/dataloop-docker:agent
```

# Scraping Prometheus Endpoints

This container will automatically scrape Prometheus metrics endpoints in containers on the same host over the Docker
172.17.x.x network. This monitoring container should be left on and does not need to be restarted - everything is dynamic.

An automated process runs every 10 seconds inside the container looking for labels applied to containers. If the label
`prometheus.port` is found the process will automatically scrape that port with the default `/metrics` path.

## Scraping Example

To automatically scrape a Prometheus node_exporter container simply start it with these options:

```
docker run -d --name node_exporter -p 9100:9100 --label prometheus.port=9100 prom/node-exporter
```

The `--label prometheus.port=9100` is the key piece of configuration that lets this container know to scrape it.

*Note:* you can optionally pass in `--label prometheus.path=/some/path` to be used instead of the default `/metrics` path.

Another useful scenario is when using the Prometheus client libraries to instrument your own applications. Expose those
metrics over `/metrics` on a given port in your container and pass in a label on startup for dynamic collection.


# Known Issues

## Amazon Linux Cgroups

If using an Amazon Linux AMI you will need to also mount the /cgroup directory into the container.

```
-v /cgroup:/sys/fs/cgroup:ro
```

## RHEL and Centos Security

RHEL and CentOS lock down their containers a bit more. cAdvisor needs access to the Docker daemon through its socket. This requires --privileged=true in RHEL and CentOS.


## Ubuntu Memory Metrics

If you see 0 for base.memory in your containers you will need to enable memory accounting in cgroups. To do that on Ubuntu update the kernel line in Grub:

https://docs.docker.com/engine/installation/linux/ubuntulinux/#adjust-memory-and-swap-accounting


## Connecting through a Proxy


If you are behind a proxy server, you can pass the standard proxy environment variables to the docker container to have data passed through:

```
docker run -e HTTP_PROXY=http://proxy:port....
```
