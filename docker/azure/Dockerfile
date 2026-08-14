FROM mcr.microsoft.com/azure-cli:2.67.0

RUN tdnf install -y bash jq grep 2>/dev/null || yum install -y bash jq grep 2>/dev/null || true

COPY scripts/setup-oidc.sh /usr/local/bin/setup-oidc
COPY scripts/verify-oidc.sh /usr/local/bin/verify-oidc
RUN sed -i 's/\r$//' /usr/local/bin/setup-oidc /usr/local/bin/verify-oidc \
    && chmod +x /usr/local/bin/setup-oidc /usr/local/bin/verify-oidc

WORKDIR /workspace
ENTRYPOINT ["setup-oidc"]
CMD ["help"]
