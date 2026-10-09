# The arm O take image: Codex CLI (its update-off switch is a per-take config setting, written by run_take's lane).
# Built only from the image.lock beside this file (box/image_lock.py build_argv: --pull=false, every build argument
# and label from the lock); nothing is built in wave 4. Nothing of the study is copied into this image.
# The base is the shared base, pinned by digest in the lock (PENDING), and it must supply node and npm.
ARG BASE
FROM ${BASE}
ARG BASE_NAME
ARG BASE_DIGEST
ARG HARNESS_VERSION
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
# The harness at the lock's exact version, then a check that the installed package is that version.
RUN npm install -g "@openai/codex@${HARNESS_VERSION}"
RUN test "$(node -p 'require(process.argv[1]).version' "$(npm root -g)/@openai/codex/package.json")" = "${HARNESS_VERSION}"
LABEL org.opencontainers.image.base.name="${BASE_NAME}"
LABEL org.opencontainers.image.base.digest="${BASE_DIGEST}"
LABEL app.cli.version="${HARNESS_VERSION}"
LABEL app.python.version="${PYTHON_VERSION}"
# run_take names the keep-alive command; the base's entrypoint is reset.
ENTRYPOINT []
USER 10001:10001
