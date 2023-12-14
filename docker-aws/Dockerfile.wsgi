# This does not inherit from a base build - The APT package requirements are so specific
# to this one Python service that it would require its own individual base build and that
# would only be used by one service - this one. So it's a fully bespoke build instead.
# Python pinned as per original project
FROM python:3.9-alpine

ENV APP_DIR=/app
ENV DEP_PYUWSGI_VERSION=2.0.22

ARG BUILD_DATE
ARG BUILD_VERSION
ARG release_name
LABEL BUILD_DATE=${BUILD_DATE}
LABEL BUILD_VERSION=${BUILD_VERSION}

WORKDIR ${APP_DIR}
COPY requirements.txt ${APP_DIR}
RUN addgroup -S uwsgi && adduser -S -H -G uwsgi uwsgi && \
    python3 -m venv venv && \
    echo ${release_name} > ${APP_DIR}/version_label && \
    apk upgrade && apk add curl gcc git libffi-dev \
    xz libpcre3-dev postgresql-dev libxml2-dev libxslt-dev \
    openssl-dev zlib-dev && \
    /app/venv/bin/pip3 install --no-cache-dir --upgrade pip pyuwsgi==${DEP_PYUWSGI_VERSION} -r requirements.txt
COPY --chown=uwsgi:uwsgi . ${APP_DIR}
CMD ["/app/venv/bin/uwsgi", "--http-socket", ":8888", "--master", "-w", "application:application"]
EXPOSE 8888
USER uwsgi
