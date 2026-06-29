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
ALLOWED_HOSTS=www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225
CSRF_TRUSTED_ORIGINS=https://www.centralretencao.com.br

DB_NAME=inventario-gtn-db
DB_USER=inventario
DB_PASSWORD=<senha-postgres>
DB_HOST=192.168.0.222
DB_PORT=5432

INVENTARIO_API_BASE_URL=http://192.168.0.216/inventario-api
TYPE_NAME=producao
ENABLE_TEST_ROUTES=False

OTEL_ENABLED=True
OTEL_EXPORTER_OTLP_ENDPOINT=http://192.168.0.213:4318
LOKI_URL=http://192.168.0.213:3100/loki/api/v1/push
LOG_LEVEL=INFO
```

**Nota:** `IMAGE` **não** entra neste arquivo — o workflow exporta `IMAGE=ghcr.io/c-trends-bpo/inventario:<sha>` no passo de deploy.

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
| Health por nó | `curl -f http://192.168.0.223:8000/health/` (e .224, .225) |
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

## Limitação conhecida (mídia local)

Com 3 réplicas e sem volume compartilhado, arquivos gravados em `MEDIA_ROOT` (ex.: extração diária de auditoria) existem apenas na réplica que gerou o arquivo. Downloads podem falhar se o HAProxy encaminhar para outro nó. Aceito nesta fase — migração prevista para API/Firebase.
