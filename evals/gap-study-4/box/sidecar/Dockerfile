# The sidecar's image (ruling C1): the same shared base, packages and users as the take images, plus the sidecar
# program at /opt/w/sidecar.py. Never used for a take. The build context is evals/gap-study-4/box/.
ARG BASE
FROM ${BASE}
ARG BASE_NAME
ARG BASE_DIGEST
ARG PYTHON_VERSION
# common:begin
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git inotify-tools procps ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN test "$(python3 -c 'import platform; print(platform.python_version())')" = "${PYTHON_VERSION}"
ENV PYTHONDONTWRITEBYTECODE=1
RUN groupadd --gid 10001 dana \
 && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/dana --shell /bin/bash dana \
 && groupadd --gid 10002 eli \
 && useradd --uid 10002 --gid 10002 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin eli
RUN git config --system --add safe.directory '*'
# common:end
COPY sidecar.py /opt/w/sidecar.py
LABEL org.opencontainers.image.base.name="${BASE_NAME}"
LABEL org.opencontainers.image.base.digest="${BASE_DIGEST}"
LABEL app.python.version="${PYTHON_VERSION}"
ENTRYPOINT []
USER 10002:10002
