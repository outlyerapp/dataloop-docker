Dataloop Docker Autodiscovery Container
=======================================

Run this container on each of your Docker hosts alongside a Dataloo linux agent. It will automatically create an agent instance inside Dataloop for each container on your host with basic operating system metrics under it.

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

To dynamically scrape Prometheus metric endpoints on containers add the label `prometheus.port=<exporter port>`. The dataloop-docker container will then
scrape those metrics dynamically over the docker 172.17.x.x network.

If using an Amazon Linux AMI you will need to also mount the /cgroup directory into the container.

```
-v /cgroup:/sys/fs/cgroup:ro
```

RHEL and CentOS lock down their containers a bit more. cAdvisor needs access to the Docker daemon through its socket. This requires --privileged=true in RHEL and CentOS.

If you see 0 for base.memory in your containers you will need to enable memory accounting in cgroups. To do that on Ubuntu update the kernel line in Grub:

https://docs.docker.com/engine/installation/linux/ubuntulinux/#adjust-memory-and-swap-accounting

Proxy
=====

If you are behind a proxy server, you can pass the standard proxy environment variables to the docker container to have data passed through:

```
docker run -e HTTP_PROXY=http://proxy:port....
```


Contributing Changes
====================

If you want to modify the container then feel free to submit a pull request. Below is the spec for what each script does.

A set of independent foreground processes that log to standard out that can be run under a supervisor.

All state is stored in Dataloop so these scripts can be run in ephemeral containers with no local storage.

- discover.py

Polls CAdvisor API and Dataloop. Ensures containers match agents via register and deregister API's.

- tag.py

Tags agents in Dataloop with their Docker Tags by matching container ID to agent name.

- metrics.py

Sends CAdvisor metrics to Dataloop via the Graphite endpoint every 10 seconds by matching container ID to agent name.

- check.py

Polls :8080/health_check for a 200 response code over docker internal network address and emits 0,1,2,3 to <fingerprint>.health_check 

### Interactive running to debug:
```
docker run --rm -t -i -e API_KEY=$API_KEY \
--volume=/:/rootfs:ro \
--volume=/var/run:/var/run:rw \
--volume=/sys:/sys:ro \
--volume=/var/lib/docker/:/var/lib/docker:ro \
dataloop/dataloop-docker:latest /sbin/my_init -- bash -l
```
