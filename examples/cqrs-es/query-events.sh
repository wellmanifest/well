#!/usr/bin/env sh
set -eu
curl -fsS 'http://localhost:8080/v1/events?stream=run:ticket-002:application:1&limit=100'
