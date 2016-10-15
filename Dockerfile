# Use phusion/baseimage as base image. To make your builds reproducible, make
# sure you lock down to a specific version, not to `latest`!
# See https://github.com/phusion/baseimage-docker/blob/master/Changelog.md for
# a list of version numbers.
FROM phusion/baseimage:latest

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

# Install Dataloop Agent
# For the python environment
RUN curl -s https://download.dataloop.io/pubkey.gpg | apt-key add - \
    && echo 'deb https://download.dataloop.io/deb/ unstable main' > /etc/apt/sources.list.d/dataloop.list \
    && apt-get update && apt-get install dataloop-agent && dpkg -l | grep dataloop
RUN /opt/dataloop/embedded/bin/pip install prometheus-client

# TODO: Install cadvisor - link to for now
ADD https://github.com/google/cadvisor/releases/download/v0.24.0-alpha1/cadvisor /opt/dataloop/embedded/bin/cadvisor
RUN chmod +x /opt/dataloop/embedded/bin/cadvisor
RUN mkdir /etc/service/cadvisor
ADD cadvisor.run /etc/service/cadvisor/run

# Dataloop Agent
RUN mkdir /etc/service/agent
ADD agent.run /etc/service/agent/run
ADD base.py /opt/dataloop/plugins

# Scripts!
COPY discover.py /opt/dataloop/embedded/bin/discover.py
COPY presence.py /opt/dataloop/embedded/bin/presence.py
COPY metrics.py /opt/dataloop/embedded/bin/metrics.py
COPY dl_lib.py /opt/dataloop/embedded/bin/dl_lib.py
COPY tag.py /opt/dataloop/embedded/bin/tag.py
COPY scrape.py /opt/dataloop/embedded/bin/scrape.py

RUN mkdir /etc/service/metrics
ADD metrics.run /etc/service/metrics/run

RUN mkdir /etc/service/discover
ADD discover.run /etc/service/discover/run

RUN mkdir /etc/service/presence
ADD presence.run /etc/service/presence/run

RUN mkdir /etc/service/tag
ADD tag.run /etc/service/tag/run

RUN mkdir /etc/service/scrape
ADD scrape.run /etc/service/scrape/run

# Disable some phusion base services
# RUN touch /etc/service/{cron,sshd,syslog-ng,syslog-forwarder}/down
RUN touch /etc/service/cron/down \
    && touch /etc/service/syslog-ng/down

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
