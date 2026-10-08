# Spike 002 verifier image: a generic Python gate runner for OpenShell.
# Follows the NVIDIA OpenShell bring-your-own-container requirements:
# standard Linux base, non-root OCI USER, writable /sandbox workspace,
# iproute2 for network-namespace isolation. CMD is replaced by the
# OpenShell supervisor, so none is declared.
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Test tooling is baked in: the gate sandbox has no network, so nothing can
# be pip-installed at gate time.
RUN pip install --no-cache-dir "pytest==8.4.2"

RUN groupadd --gid 1500 app \
    && useradd --uid 1500 --gid app --create-home app

RUN install -d -o app -g app /sandbox

# Control directory for the filesystem probe: Unix permissions allow the
# sandbox user to write here, but the policy does not list it. A failed write
# here can only come from OpenShell's Landlock enforcement, not from DAC.
RUN install -d -m 0777 /opt/omega-dac-writable

WORKDIR /sandbox
USER app
