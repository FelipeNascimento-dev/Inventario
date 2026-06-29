#!/usr/bin/env bash
# Força todas as réplicas de inventario_gtn_web para a mesma tag de imagem.
# Use quando docker service ps mostrar tags diferentes entre nós Running.
#
# Executar no MANAGER do Swarm (ex.: python-app-01), com docker login ghcr.io ativo.
#
# Uso:
#   bash deploy/scripts/force-inventario-gtn-image-rollout.sh <tag-ou-sha>
#   bash deploy/scripts/force-inventario-gtn-image-rollout.sh 455ba54c60ec94b92c409b469be84f9e8e9c49e2
#
set -euo pipefail

SERVICE_NAME="inventario_gtn_web"
IMAGE_REPO="ghcr.io/c-trends-bpo/inventario"
TAG="${1:-}"

if [[ -z "${TAG}" ]]; then
  echo "Informe a tag (commit SHA) da imagem desejada." >&2
  echo "Ex.: bash $0 455ba54c60ec94b92c409b469be84f9e8e9c49e2" >&2
  exit 1
fi

FULL_IMAGE="${IMAGE_REPO}:${TAG}"

if ! docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null | grep -q true; then
  echo "AVISO: este host pode não ser manager do Swarm. Rode no python-app-01." >&2
fi

echo "=== Imagens Running antes ==="
docker service ps "${SERVICE_NAME}" \
  --filter "desired-state=running" \
  --format '{{.Node}} {{.Image}}' | sort -u || true

echo "=== Pull ${FULL_IMAGE} (manager) ==="
if ! docker pull "${FULL_IMAGE}"; then
  echo "Falha no pull. A tag existe no GHCR? Pacote com permissão de pull?" >&2
  exit 1
fi

echo "=== service update (stop-first — obrigatório com porta mode: host) ==="
docker service update \
  --image "${FULL_IMAGE}" \
  --with-registry-auth \
  --update-parallelism 1 \
  --update-delay 10s \
  --update-order stop-first \
  "${SERVICE_NAME}"

echo "=== Aguardando 3 réplicas na mesma tag (até 10 min) ==="
DESIRED=3
TIMEOUT=600
ELAPSED=0

while [[ "${ELAPSED}" -lt "${TIMEOUT}" ]]; do
  MATCHING=$(docker service ps "${SERVICE_NAME}" \
    --filter "desired-state=running" \
    --format '{{.Image}}' \
    | awk -v tag="${TAG}" '$0 ~ tag { c++ } END { print c + 0 }')
  RUNNING=$(docker service ps "${SERVICE_NAME}" \
    --filter "desired-state=running" \
    --format '{{.CurrentState}}' \
    | awk '$1 == "Running" { c++ } END { print c + 0 }')
  echo "  ${ELAPSED}s — Running ${RUNNING}/${DESIRED}, tag ${TAG}: ${MATCHING}/${DESIRED}"
  if [[ "${MATCHING}" -eq "${DESIRED}" ]] && [[ "${RUNNING}" -eq "${DESIRED}" ]]; then
    echo "OK — todas as réplicas na imagem ${FULL_IMAGE}"
    docker service ps "${SERVICE_NAME}" \
      --filter "desired-state=running" \
      --format '{{.Node}} {{.Image}}'
    exit 0
  fi
  sleep 15
  ELAPSED=$((ELAPSED + 15))
done

echo "Timeout — verifique Rejected (No such image) ou porta em uso:" >&2
docker service ps "${SERVICE_NAME}" --no-trunc | head -25
exit 1
