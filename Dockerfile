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
    && echo 'deb https://download.dataloop.io/deb/ stable main' > /etc/apt/sources.list.d/dataloop.list \
    && apt-get update && sudo apt-get install dataloop-agent


# TODO: Install cadvisor - link to for now
ADD https://github.com/google/cadvisor/releases/download/0.18.0/cadvisor /opt/dataloop/embedded/bin/cadvisor
RUN chmod +x /opt/dataloop/embedded/bin/cadvisor
RUN mkdir /etc/service/cadvisor
ADD cadvisor.run /etc/service/cadvisor/run

# Scripts!
COPY discover.py /opt/dataloop/embedded/bin/discover.py
COPY metrics.py /opt/dataloop/embedded/bin/metrics.py

RUN mkdir /etc/service/metrics
ADD metrics.run /etc/service/metrics/run

RUN mkdir /etc/service/discover
ADD discover.run /etc/service/discover/run

RUN mkdir /etc/service/tag
ADD tag.run /etc/service/tag/run

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
