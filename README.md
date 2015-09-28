### Dataloop Docker Autodiscovery Container

A set of independent foreground processes that log to standard out that can be run under a supervisor.

All state is stored in Dataloop so these scripts can be run in ephemeral containers with no local storage.

- discover.py

Polls CAdvisor API and Dataloop. Ensures containers match agents via register and deregister API's.

- tag.py

Tags agents in Dataloop with their Docker Tags by matching container ID to agent name.

- metrics.py

Sends CAdvisor metrics to Dataloop via the Graphite endpoint every 30 seconds by matching container ID to agent name.

- check.py

Polls :8080/health_check for a 200 response code over docker internal network address and emits 0,1,2,3 to <fingerprint>.health_check
