FROM dataloop/agent-base

ENV GLIBC_VERSION "2.23-r3"

RUN apk --no-cache add ca-certificates wget device-mapper gcc python-dev && \
    apk --no-cache add zfs --repository http://dl-3.alpinelinux.org/alpine/edge/main/ && \
    wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://raw.githubusercontent.com/sgerrand/alpine-pkg-glibc/master/sgerrand.rsa.pub && \
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/${GLIBC_VERSION}/glibc-${GLIBC_VERSION}.apk && \
    wget https://github.com/andyshinn/alpine-pkg-glibc/releases/download/${GLIBC_VERSION}/glibc-bin-${GLIBC_VERSION}.apk && \
    apk add glibc-${GLIBC_VERSION}.apk glibc-bin-${GLIBC_VERSION}.apk && \
    /usr/glibc-compat/sbin/ldconfig /lib /usr/glibc-compat/lib && \
    echo 'hosts: files mdns4_minimal [NOTFOUND=return] dns mdns4' >> /etc/nsswitch.conf && \
    rm -rf /var/cache/apk/*

RUN mkdir -p /opt/dataloop/embedded/bin && wget -q -O /opt/dataloop/embedded/bin/cadvisor https://github.com/google/cadvisor/releases/download/v0.24.1/cadvisor

RUN chmod +x /opt/dataloop/embedded/bin/cadvisor && ln -s /usr/bin/python /opt/dataloop/embedded/bin/python

COPY requirements.txt /
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Scripts!
COPY discover.py presence.py metrics.py dl_lib.py tag.py /opt/dataloop/embedded/bin/

COPY agent.run cadvisor.run metrics.run discover.run presence.run tag.run start.sh /run/

ENTRYPOINT ["sh", "-c"]
CMD ["/run/start.sh"]
