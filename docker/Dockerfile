ARG PIXI_VERSION=0.67.0
FROM ghcr.io/prefix-dev/pixi:${PIXI_VERSION} AS pixi-source

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        git \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=pixi-source /usr/local/bin/pixi /usr/local/bin/pixi

WORKDIR /app

# Copy dependency metadata first to preserve cache layers when possible.
COPY pixi.toml pyproject.toml README.md LICENSE.md noxfile.py /app/
COPY prepmd /app/prepmd

RUN pixi install

# Copy files used by lint/type/test/docs sessions.
COPY tests /app/tests
COPY docs /app/docs
COPY examples /app/examples
COPY .pre-commit-config.yaml .readthedocs.yml Makefile CHANGELOG.md CONTRIBUTING.md /app/

COPY docker/entrypoint.sh /usr/local/bin/prepmd-entrypoint
RUN chmod +x /usr/local/bin/prepmd-entrypoint

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/prepmd-entrypoint"]
CMD []
