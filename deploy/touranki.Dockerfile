FROM alpine:3.23@sha256:85fe1e81d6758c208f3e1eed4338a1997e19d4be002d4dd32d3100c9a8c010a0

# BusyBox provides wget; the statically linked server needs no added packages.
RUN addgroup -S -g 10001 touranki \
    && adduser -S -D -H -u 10001 -G touranki touranki

COPY --chown=10001:10001 --chmod=0555 build/touranki/touranki-server /usr/local/bin/touranki-server

USER 10001:10001
ENV TOURANKI_ADDR=:8080
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/touranki-server"]
