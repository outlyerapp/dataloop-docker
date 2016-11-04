#!/usr/bin/env sh
export AGENT_API_KEY=$API_KEY
/run/cadvisor.run &
/run/discover.run &
/run/presence.run &
/run/metrics.run &
/run/tag.run &
