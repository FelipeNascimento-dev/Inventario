# Configuração manual no servidor — Inventario GTN (Docker Swarm)

Procedimentos executados **uma vez** (ou quando mudar infra) no cluster `python-app-01` / `python-app-02` / `python-app-03`. O deploy contínuo é feito pelo workflow `.github/workflows/deploy-swarm.yml` em push na branch `main`.

---

## 1. GitHub Actions self-hosted runner

Instalar e registrar o runner em `python-app-01` (manager/leader), com acesso ao Docker Swarm e ao socket Docker.

### Labels obrigatórias

```text
self-hosted
linux
swarm
```

Labels opcionais recomendadas (documentação/organização):

```text
python-app
deploy
```

### Verificação

No repositório GitHub: **Settings → Actions → Runners** — o runner deve aparecer **Idle** com as labels acima.

No servidor:

```bash
sudo systemctl status actions.runner.*
```

O usuário do runner precisa pertencer ao grupo `docker`:

```bash
sudo usermod -aG docker <usuario-do-runner>
```

---

## 2. Arquivo de ambiente `/opt/envs/inventario-gtn.env`

Criar no **manager** (`python-app-01`). Não versionar no Git.

```bash
sudo mkdir -p /opt/envs
sudo touch /opt/envs/inventario-gtn.env
sudo chmod 600 /opt/envs/inventario-gtn.env
sudo chown <usuario-do-runner>:<grupo-do-runner> /opt/envs/inventario-gtn.env
```

Conteúdo (preencher valores reais de produção; modelo em `.env.example` na raiz do repositório):

```env
DJANGO_SETTINGS_MODULE=setup.settings
DEBUG=False
SECRET_KEY=<gerar-chave-segura>
ALLOWED_HOSTS=localhost,127.0.0.1,www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225,192.168.0.213
CSRF_TRUSTED_ORIGINS=https://www.centralretencao.com.br

DB_NAME=inventario-gtn-db
DB_USER=inventario
DB_PASSWORD=<senha-postgres>
DB_HOST=192.168.0.222
DB_PORT=5432

INVENTARIO_API_BASE_URL=http://192.168.0.216/inventario-api
TYPE_NAME=producao
ENABLE_TEST_ROUTES=False

APP_PORT=8000

OTEL_ENABLED=True
OTEL_APPEND_IP_SUFFIX=False
OTEL_EXPORTER_OTLP_ENDPOINT=http://192.168.0.213:4318
LOKI_URL=http://192.168.0.213:3100/loki/api/v1/push
LOG_LEVEL=INFO
```

**Nota:** `IMAGE` **não** entra neste arquivo — o workflow exporta `IMAGE=ghcr.io/c-trends-bpo/inventario:<sha>` no passo de deploy.

`APP_PORT=8000` é a porta escolhida para o Inventario GTN neste cluster. Novas aplicações devem usar porta diferente — ver seção 5.2 em `docs/contexto_infra_swarm_cursor.md`.

**Importante:** incluir `localhost,127.0.0.1` no início de `ALLOWED_HOSTS`. O healthcheck interno do Docker Swarm usa `Host: localhost` (ou IP loopback); sem esses hosts, Django retorna `400 DisallowedHost` e o Swarm encerra a task após ~2 minutos. **Não** duplicar o nome da variável no valor (typo comum: `ALLOWED_HOSTS=ALLOWED_HOSTS=...`).

Correção rápida no servidor (sem esperar deploy):

```bash
bash deploy/scripts/fix-inventario-gtn-allowed-hosts.sh
```

Ou manualmente:

```bash
sudo sed -i 's/^ALLOWED_HOSTS=ALLOWED_HOSTS=/ALLOWED_HOSTS=/' /opt/envs/inventario-gtn.env
sudo grep ALLOWED_HOSTS /opt/envs/inventario-gtn.env
docker service update --env-add ALLOWED_HOSTS=localhost,127.0.0.1,www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225,192.168.0.213 --force inventario_gtn_web
```

### Gerar `SECRET_KEY` (exemplo)

```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 3. Rede overlay `app_network`

Se ainda não existir no Swarm (executar em um manager):

```bash
docker network create \
  --driver overlay \
  --attachable \
  app_network
```

Verificar:

```bash
docker network ls | grep app_network
```

---

## 4. GHCR — visibilidade do pacote

O workflow usa `GITHUB_TOKEN` com `permissions.packages: write` (sem PAT dedicado na fase inicial).

Após o primeiro push em `main`:

1. Abrir **Packages** no GitHub → pacote `inventario` (ou nome derivado do repositório).
2. Garantir visibilidade **internal** ou vinculada ao repositório, para os nós do Swarm puxarem a imagem via `docker stack deploy --with-registry-auth`.

Fallback (só se necessário): secrets `GHCR_USER` + `GHCR_PAT` — ver `docs/contexto_infra_swarm_cursor.md` seção 18.

---

## 5. HAProxy — backend Inventario GTN

Adicionar ou ajustar no HAProxy existente (domínio/backend conforme ambiente real):

```haproxy
backend inventario_gtn
    balance roundrobin
    option httpchk GET /health/
    http-check expect status 200-399

    server python-app-01 192.168.0.223:8000 check
    server python-app-02 192.168.0.224:8000 check
    server python-app-03 192.168.0.225:8000 check
```

Vincular o frontend (ACL/host) ao backend `inventario_gtn` conforme o virtual host de produção (ex.: `www.centralretencao.com.br`).

**Importante:** encaminhar o path **completo** (`/inventario/...`, `/health/`). Não remover o prefixo `/inventario` no HAProxy — caso contrário o Django retorna 404 em rotas como `/inventario/login/` (ver seção 20 em `docs/contexto_infra_swarm_cursor.md`).

Recarregar HAProxy após editar a configuração:

```bash
# comando exato depende da instalação (systemd, service, etc.)
sudo systemctl reload haproxy
```

---

## 6. Portainer (opcional)

Agent Swarm em `192.168.0.223:9001` — apenas visualização; deploy via GitHub Actions, não via Portainer.

---

## 7. Checklist pós-configuração

| Item | Comando / verificação |
|------|------------------------|
| Runner online | GitHub → Actions → Runners |
| Env file | `ls -la /opt/envs/inventario-gtn.env` (modo 600) |
| Swarm saudável | `docker node ls` — 3 managers |
| Rede | `docker network inspect app_network` |
| Primeiro deploy | push em `main` ou re-run do workflow |
| Réplicas | `docker stack ps inventario_gtn` — 3 running |
| Health por nó | `curl -f http://192.168.0.223:8000/health/` (e .224, .225) — porta `APP_PORT` |
| Hostname estável | `docker service ps inventario_gtn_web` — `inventario-gtn-python-app-0X` por nó |
| Logs Loki | `{app="Inventario GTN-producao"}` — sem sufixo de IP (`OTEL_APPEND_IP_SUFFIX=False`) |
| HAProxy | backends green no painel/stats do HAProxy |
| Rotas de teste off | `ENABLE_TEST_ROUTES=False` → `/inventario/teste-erro-loki/` retorna 404 |

---

## 8. Comandos úteis

```bash
# Status da stack
docker stack services inventario_gtn
docker stack ps inventario_gtn --no-trunc

# Logs
docker service logs -f inventario_gtn_web

# Rollback manual (se necessário)
docker service rollback inventario_gtn_web
```

---

## 9. Troubleshooting — réplicas `Shutdown Complete` após ~2 minutos

### Sintoma

```bash
docker service ls | grep inventario
# 0/3 ou ciclo constante — nunca estabiliza 3/3

docker service ps inventario_gtn_web --filter "desired-state=shutdown" | head -5
# Shutdown Complete em todas, coluna ERROR vazia, ~130s após start
```

HAProxy pode continuar marcando backends como saudáveis (healthcheck no IP do nó, que está em `ALLOWED_HOSTS`), enquanto o Swarm mata o container por falha no healthcheck **interno**.

### Causa raiz

1. **`ALLOWED_HOSTS` malformado** — typo `ALLOWED_HOSTS=ALLOWED_HOSTS=localhost,...` faz Django interpretar o primeiro host como literal `ALLOWED_HOSTS=localhost`.
2. **`localhost` / `127.0.0.1` ausentes** — healthcheck Docker usa `curl http://localhost:$APP_PORT/health/`; `SecurityMiddleware` rejeita com `400 DisallowedHost` antes da view.

Timing típico: `start_period: 40s` + `interval: 30s` × `retries: 3` ≈ **100–130 segundos**.

### Diagnóstico

```bash
grep ALLOWED_HOSTS /opt/envs/inventario-gtn.env
# Deve haver UMA ocorrência de "ALLOWED_HOSTS=" no início da linha

CONTAINER_ID=$(docker ps -q --filter "name=inventario_gtn_web" | head -1)
docker exec "$CONTAINER_ID" curl -sv http://localhost:8000/health/ 2>&1 | tail -20
# 400 + Invalid HTTP_HOST header: 'localhost' confirma a causa

docker service logs inventario_gtn_web --tail 200 2>&1 | grep -iE "health|disallowed|400" || true
```

### Correção

```bash
# Opção A — script do repositório (no manager, após checkout ou copiar o script)
bash deploy/scripts/fix-inventario-gtn-allowed-hosts.sh

# Opção B — manual
sudo nano /opt/envs/inventario-gtn.env
# Linha correta (sem duplicar o nome da variável):
# ALLOWED_HOSTS=localhost,127.0.0.1,www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225,192.168.0.213

docker service update \
  --env-add ALLOWED_HOSTS=localhost,127.0.0.1,www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225,192.168.0.213 \
  --force inventario_gtn_web
```

Aguardar ~3 minutos e validar:

```bash
docker service ls | grep inventario          # 3/3
docker exec $(docker ps -q --filter "name=inventario_gtn_web" | head -1) curl -f http://localhost:8000/health/
```

### Prevenção (repositório)

- `.env.example` e esta documentação incluem `localhost,127.0.0.1`.
- `deploy/stack.yml` usa healthcheck com `-H 'Host: www.centralretencao.com.br'` e `127.0.0.1` (resiliente mesmo se alguém esquecer localhost no `.env`).
- Workflow `deploy-swarm.yml` valida `APP_PORT`, corrige typo `ALLOWED_HOSTS=ALLOWED_HOSTS=`, executa migrations, faz **`docker pull`** da imagem do commit, usa **`CACHE_BUST`** no build (evita HTML antigo por cache do runner) e aguarda `3/3` réplicas estáveis (timeout **600s**) antes de concluir o job.

### Actions falhou em `Wait for replicas` mas app está no ar

O `docker stack deploy` já aplica a stack antes do wait. Se o job falhar por timeout mas `docker service ls` mostrar `3/3` minutos depois, foi falso negativo do polling — re-run do workflow ou ignorar se o cluster já está estável.

```bash
docker service ls | grep inventario_gtn    # esperado: 3/3
docker stack ps inventario_gtn
```

### Deploy OK mas HTML/template não mudou

Não é cache do Django. Verificar se **todas** as réplicas usam a **mesma tag**:

```bash
docker service ps inventario_gtn_web --filter "desired-state=running" --format '{{.Node}} {{.Image}}'
```

Se aparecerem **duas tags** (ex.: `98809def...` e `455ba54...`), o HAProxy alterna versão antiga e nova — parece que “não mudou” ou muda só às vezes.

Correção imediata (substitua pelo SHA do commit desejado):

```bash
bash deploy/scripts/force-inventario-gtn-image-rollout.sh 455ba54c60ec94b92c409b469be84f9e8e9c49e2
```

**Importante:** rodar no **manager do Swarm** (`python-app-01`), não em outro host. O script usa `stop-first` (porta `mode: host` não suporta `start-first`).

Diagnóstico do arquivo no container:

```bash
docker exec $(docker ps -q --filter "name=inventario_gtn_web" | head -1) \
  head -20 /app/inventario/templates/inventario/index.html
```

Se o arquivo no container estiver antigo: cache de build no runner (`CACHE_BUST`) ou pull falho nos nós. Ver seção 17 em `docs/contexto_infra_swarm_cursor.md`.

---

## 10. Troubleshooting — rollback `host-mode port already in use` / `No such image`

### Sintoma

```text
No such image: ghcr.io/c-trends-bpo/inventario:<sha>
no suitable node (host-mode port already in use on 3 nodes)
rollback: update rolled back due to failure...
```

### Causas

| Erro | Causa |
|------|--------|
| `No such image` | Tag inexistente no GHCR, ou nós do Swarm sem credencial para pull (`docker login ghcr.io` + `--with-registry-auth`) |
| `port already in use` | `update_config.order: start-first` com porta **`mode: host`** — novo container sobe antes de liberar a porta 8000 no nó |

### Correção

1. Confirmar que a tag existe: `docker pull ghcr.io/c-trends-bpo/inventario:<sha>` no **manager**.
2. `deploy/stack.yml` deve usar **`order: stop-first`** no `update_config` (já corrigido no repositório).
3. Forçar rollout no manager:

```bash
bash deploy/scripts/force-inventario-gtn-image-rollout.sh <sha>
```

4. Se `No such image` persistir nos workers: em cada `python-app-0X`, executar uma vez `docker login ghcr.io` (PAT com `read:packages`) ou garantir pacote GHCR **internal** vinculado ao org.

Com `stop-first`, há ~30–60s de indisponibilidade **por nó** durante o update; os outros 2 nós continuam atendendo via HAProxy.

---

Com 3 réplicas e sem volume compartilhado, arquivos gravados em `MEDIA_ROOT` (ex.: extração diária de auditoria) existem apenas na réplica que gerou o arquivo. Downloads podem falhar se o HAProxy encaminhar para outro nó. Aceito nesta fase — migração prevista para API/Firebase.
