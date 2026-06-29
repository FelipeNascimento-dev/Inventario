#!/usr/bin/env bash
# Corrige ALLOWED_HOSTS malformado em /opt/envs/inventario-gtn.env e força recriação do serviço.
# Executar no manager (python-app-01) com usuário que possui o env file e acesso ao Docker Swarm.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/opt/envs/inventario-gtn.env}"
SERVICE_NAME="${SERVICE_NAME:-inventario_gtn_web}"
CORRECT_ALLOWED_HOSTS="localhost,127.0.0.1,www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225,192.168.0.213"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Arquivo não encontrado: ${ENV_FILE}" >&2
  exit 1
fi

CURRENT=$(grep -E '^ALLOWED_HOSTS=' "${ENV_FILE}" || true)
echo "Antes: ${CURRENT:-<ausente>}"

# Remove prefixo duplicado ALLOWED_HOSTS=ALLOWED_HOSTS=
if grep -qE '^ALLOWED_HOSTS=ALLOWED_HOSTS=' "${ENV_FILE}"; then
  sed -i 's/^ALLOWED_HOSTS=ALLOWED_HOSTS=/ALLOWED_HOSTS=/' "${ENV_FILE}"
  echo "Corrigido prefixo duplicado ALLOWED_HOSTS="
fi

# Garante valor correto (substitui linha inteira)
if ! grep -qE "^ALLOWED_HOSTS=${CORRECT_ALLOWED_HOSTS}$" "${ENV_FILE}"; then
  if grep -qE '^ALLOWED_HOSTS=' "${ENV_FILE}"; then
    sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${CORRECT_ALLOWED_HOSTS}|" "${ENV_FILE}"
  else
    echo "ALLOWED_HOSTS=${CORRECT_ALLOWED_HOSTS}" >> "${ENV_FILE}"
  fi
  echo "ALLOWED_HOSTS atualizado para valor esperado."
fi

echo "Depois: $(grep -E '^ALLOWED_HOSTS=' "${ENV_FILE}")"

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

docker service update \
  --env-add "ALLOWED_HOSTS=${CORRECT_ALLOWED_HOSTS}" \
  --force \
  "${SERVICE_NAME}"

echo "Serviço ${SERVICE_NAME} atualizado. Aguarde ~3 min e valide:"
echo "  docker service ls | grep inventario"
echo "  docker exec \$(docker ps -q --filter \"name=${SERVICE_NAME}\" | head -1) curl -f http://localhost:\${APP_PORT:-8000}/health/"
