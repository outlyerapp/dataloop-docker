Dataloop Docker Autodiscovery Container
=======================================

This container contains a Dataloop agent, CAdvisor and some magic scripts that create virtual agents in Dataloop for each
running container. Depending on which OS you are running on your Docker hosts you may need to add different run options.

This container builds on [dataloop/agent-base](https://github.com/dataloop/docker-alpine/tree/master/agent-base) where further options to pass to the container can be found.

## Most Linuxes

```
DATALOOP_AGENT_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATALOOP_NAME=docker_container_name
docker run -d -e "DATALOOP_AGENT_KEY=${DATALOOP_AGENT_KEY}" \
-e "DATALOOP_NAME=${DATALOOP_NAME}" \
-p 8000:8000 \
-p 8080:8080 \
--volume=/:/rootfs:ro \
--volume=/var/run:/var/run:rw \
--volume=/sys:/sys:ro \
--volume=/var/lib/docker/:/var/lib/docker:ro \
dataloop/dataloop-docker:latest
```

## Amazon Linux

If using an Amazon Linux AMI you will need to also mount the /cgroup directory into the container.

```
DATALOOP_AGENT_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATALOOP_NAME=docker_container_name
docker run -d -e "DATALOOP_AGENT_KEY=${DATALOOP_AGENT_KEY}" \
-e "DATALOOP_NAME=${DATALOOP_NAME}" \
-p 8000:8000 \
-p 8080:8080 \
--volume=/:/rootfs:ro \
--volume=/var/run:/var/run:rw \
--volume=/sys:/sys:ro \
--volume=/var/lib/docker/:/var/lib/docker:ro \
--volume=/cgroup:/sys/fs/cgroup:ro \
dataloop/dataloop-docker:latest
```

## RHEL and CentOS

RHEL and CentOS lock down their containers a bit more. cAdvisor needs access to the Docker daemon through its socket. This requires --privileged=true in RHEL and CentOS.

```
DATALOOP_AGENT_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATALOOP_NAME=docker_container_name
docker run -d -e "DATALOOP_AGENT_KEY=${DATALOOP_AGENT_KEY}" \
-e "DATALOOP_NAME=${DATALOOP_NAME}" \
-p 8000:8000 \
-p 8080:8080 \
--privileged=true \
--volume=/:/rootfs:ro \
--volume=/var/run:/var/run:rw \
--volume=/sys:/sys:ro \
--volume=/var/lib/docker/:/var/lib/docker:ro \
--volume=/cgroup:/sys/fs/cgroup:ro \
dataloop/dataloop-docker:latest
```

# Troubleshooting

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

A set of independent foreground processes that log to standard out that can be run under a [s6-svc](http://skarnet.org/software/s6/)

All state is stored in Dataloop so these scripts can be run in ephemeral containers with no local storage.

- discover.py

Polls CAdvisor API and Dataloop. Ensures containers match agents via register and deregister API's.

- tag.py

Tags agents in Dataloop with their Docker Tags by matching container ID to agent name.

- metrics.py

Sends CAdvisor metrics to Dataloop via the Graphite endpoint every 10 seconds by matching container ID to agent name.
