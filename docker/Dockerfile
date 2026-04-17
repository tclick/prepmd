FROM python:3.13-slim

ARG PIXI_VERSION=v0.67.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        git \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/prefix-dev/pixi/releases/download/${PIXI_VERSION}/pixi-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C /usr/local/bin pixi

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
