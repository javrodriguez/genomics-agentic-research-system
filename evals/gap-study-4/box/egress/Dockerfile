# The egress proxy's image: squid at the lock's exact package version, on a base pinned by digest in its own lock.
# Nothing is copied in: run_take mounts the rendered configuration read-only at /etc/squid/squid.conf and runs
# ["squid", "-N", "-f", "/etc/squid/squid.conf"] as squid's package user (both from box/egress/proxy_conf.py).
ARG BASE
FROM ${BASE}
ARG BASE_NAME
ARG BASE_DIGEST
ARG SQUID_VERSION
RUN apt-get update \
 && apt-get install -y --no-install-recommends "squid=${SQUID_VERSION}" \
 && rm -rf /var/lib/apt/lists/*
LABEL org.opencontainers.image.base.name="${BASE_NAME}"
LABEL org.opencontainers.image.base.digest="${BASE_DIGEST}"
LABEL app.squid.version="${SQUID_VERSION}"
ENTRYPOINT []
