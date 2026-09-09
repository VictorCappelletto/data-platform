FROM alpine:3.20

ARG SOPS_VERSION=3.9.4
ARG AGE_VERSION=1.2.1

RUN apk add --no-cache bash curl coreutils grep

RUN curl -fsSL "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64" \
      -o /usr/local/bin/sops \
    && chmod +x /usr/local/bin/sops

RUN curl -fsSL "https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz" \
      -o /tmp/age.tar.gz \
    && tar -xzf /tmp/age.tar.gz -C /usr/local/bin --strip-components=1 \
    && rm /tmp/age.tar.gz

COPY scripts/secrets.sh /usr/local/bin/secrets
RUN sed -i 's/\r$//' /usr/local/bin/secrets && chmod +x /usr/local/bin/secrets

WORKDIR /workspace
ENTRYPOINT ["secrets"]
CMD ["help"]
