# This does not inherit from a base build - The package requirements are so specific
# to this one Python service that it would require its own individual base build and that
# would only be used by one service - this one. So it's a fully bespoke build instead.
# Python pinned as per original project
FROM python:3.9-alpine AS base

ENV APP_DIR=/app
ENV DEP_PYUWSGI_VERSION=2.0.22
ARG release_name

WORKDIR ${APP_DIR}
COPY requirements.txt ${APP_DIR}
RUN python3 -m venv venv && \
    echo ${release_name} > ${APP_DIR}/version_label && \
    apk add build-base git libffi-dev \
    xz pcre-dev libpq-dev libxml2-dev libxslt-dev \
    openssl-dev zlib-dev && \
    /app/venv/bin/pip install --no-cache-dir --upgrade pip pyuwsgi==${DEP_PYUWSGI_VERSION} -r requirements.txt

# Runtime stage
FROM python:3.9-alpine
ENV APP_DIR=/app
ARG BUILD_DATE
ARG BUILD_VERSION
LABEL BUILD_DATE=${BUILD_DATE}
LABEL BUILD_VERSION=${BUILD_VERSION}
RUN apk upgrade && apk add --no-cache curl libpq && rm -rf /var/cache/apk

WORKDIR ${APP_DIR}
COPY --from=base /app/venv /app/venv
COPY --chown=uwsgi:uwsgi . ${APP_DIR}

ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN addgroup -S uwsgi && adduser -S -H -G uwsgi uwsgi

CMD ["uwsgi", "--http-socket", ":8888", "--master", "-w", "application:application"]
EXPOSE 8888
USER uwsgi
