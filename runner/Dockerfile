FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    qemu-user-static \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /sandbox

WORKDIR /sandbox

# Container descartável — não tem ENTRYPOINT fixo
# É invocado com: docker run --rm -v <dir>:/sandbox simples-runner /usr/bin/qemu-i386-static /sandbox/programa
