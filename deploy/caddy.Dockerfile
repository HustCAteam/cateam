# The pinned builder uses Go 1.27.3 with the CVE-2026-111943 distrust fix.
FROM caddy:2.11.7-builder-alpine@sha256:bb53bc0dd94d5e93eca88bac50e435fd5f9dc6cc828fc6140086f282fb329e92 AS build
ARG GOPROXY=https://goproxy.cn,direct
RUN GOTOOLCHAIN=local xcaddy build v2.11.7 --output /usr/bin/caddy

FROM caddy:2.11.7-alpine@sha256:24ec7b05bc532c7bb57f727030c5056e257ff7138b4b50460306819ff79362bd
COPY --from=build /usr/bin/caddy /usr/bin/caddy
