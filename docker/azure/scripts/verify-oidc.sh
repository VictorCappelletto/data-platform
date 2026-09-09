#!/usr/bin/env bash
set -euo pipefail

OIDC_FILE="${OIDC_OUTPUT_FILE:-config/azure/oidc.generated.env}"

[[ -f "${OIDC_FILE}" ]] || { echo "Missing ${OIDC_FILE} — run setup-oidc setup first" >&2; exit 1; }

while IFS= read -r line || [[ -n "${line}" ]]; do
  line="${line%%$'\r'}"
  [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  case "${key}" in
    AZURE_CLIENT_ID|AZURE_TENANT_ID|AZURE_SUBSCRIPTION_ID)
      if [[ -z "${value}" ]]; then
        echo "Empty ${key}" >&2
        exit 1
      fi
      ;;
  esac
done < "${OIDC_FILE}"

echo "OIDC config file OK: ${OIDC_FILE}"
grep -E '^AZURE_(CLIENT_ID|TENANT_ID|SUBSCRIPTION_ID|RESOURCE_GROUP)=' "${OIDC_FILE}" | sed 's/=.*/=***/'
