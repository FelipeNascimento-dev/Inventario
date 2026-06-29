# CONTEXTO DE INFRA PARA CURSOR - DEPLOY EM DOCKER SWARM

## Objetivo deste arquivo

Este arquivo deve ser usado como contexto no Cursor para adaptar um projeto Django ou FastAPI para rodar em produção dentro da infraestrutura criada.

A aplicação deverá ser containerizada, publicada em Docker Swarm, gerenciada visualmente pelo Portainer e exposta externamente pelo HAProxy já existente.

---

# 1. Visão geral da infraestrutura

A infraestrutura criada possui servidores Linux para aplicações Python, usando Docker Swarm.

## Servidores do cluster

```text
192.168.0.223 python-app-01
192.168.0.224 python-app-02
192.168.0.225 python-app-03
```

## Estado esperado do Swarm

Os três servidores devem atuar como Docker Swarm Manager.

```text
python-app-01 - Manager / Leader
python-app-02 - Manager / Reachable
python-app-03 - Manager / Reachable
```

O cluster pode começar com apenas dois servidores e adicionar o terceiro depois.

Quando existirem apenas dois servidores ativos, stacks com `replicas: 3` e `max_replicas_per_node: 1` deixarão uma réplica pendente até o terceiro nó entrar.

---

# 2. Entrada externa e balanceamento

O HAProxy já existe na frente da infraestrutura e continuará sendo o balanceador externo.

O Docker Swarm será usado para orquestrar os containers, mas a entrada principal de tráfego será feita pelo HAProxy.

Fluxo esperado:

```text
Usuário / Sistema externo
        ↓
HAProxy
        ↓
python-app-01 / python-app-02 / python-app-03
        ↓
Containers Docker Swarm
        ↓
Aplicação Django ou FastAPI
```

---

# 3. Decisão de rede no Swarm

Como já existe HAProxy na frente, as aplicações devem publicar portas em modo `host`, e não depender do routing mesh padrão do Swarm.

Usar este padrão nas stacks:

```yaml
ports:
  - target: ${APP_PORT}
    published: ${APP_PORT}
    protocol: tcp
    mode: host
```

`${APP_PORT}` é substituído no `docker stack deploy` a partir do `.env` do servidor. Ver seção 5.2 — **perguntar a porta** antes de definir.

Motivo:

- O HAProxy consegue checar diretamente cada servidor.
- A porta só fica aberta no servidor onde o container está rodando.
- O health check do HAProxy fica mais confiável.
- Evita dupla camada de balanceamento: HAProxy + ingress routing mesh.

**Rolling update:** com `mode: host`, usar `deploy.update_config.order: stop-first`. Com `start-first`, o Swarm tenta subir o novo container antes de parar o antigo no mesmo nó e a porta publicada já está em uso → `host-mode port already in use` e rollback.

---

# 4. Rede overlay padrão

A rede overlay das aplicações se chama:

```text
app_network
```

Ela foi criada no Swarm com:

```bash
docker network create \
  --driver overlay \
  --attachable \
  app_network
```

Toda stack de aplicação deve usar:

```yaml
networks:
  app_network:
    external: true
```

---

# 5. Padrão de réplicas

Cada aplicação deve iniciar com uma réplica por servidor.

Usar este padrão:

```yaml
deploy:
  mode: replicated
  replicas: 3
  placement:
    max_replicas_per_node: 1
```

Se o cluster ainda tiver apenas dois servidores, usar temporariamente:

```yaml
replicas: 2
```

Depois que `python-app-03` entrar no Swarm, alterar para:

```yaml
replicas: 3
```

---

## 5.1 Nomenclatura fixa e rolling update

Cada aplicação deve usar nomes **estáveis** entre deploys. O Swarm substitui tasks no rolling update (o ID da task muda), mas o serviço e o hostname por nó permanecem previsíveis.

| Elemento | Exemplo Inventario GTN | Regra geral |
|----------|------------------------|-------------|
| `STACK_NAME` | `inventario_gtn` | Definir uma vez no workflow; **nunca** mudar entre deploys |
| Serviço Swarm | `inventario_gtn_web` | `{STACK_NAME}_{nome_do_servico}` |
| Hostname do container | `inventario-gtn-{{.Node.Hostname}}` | Template Swarm; previsível por nó |

Incluir no `deploy/stack.yml`:

```yaml
hostname: "minha-app-{{.Node.Hostname}}"
```

Substituir `minha-app` pelo identificador curto da aplicação (ex.: `inventario-gtn`).

### Comportamento esperado

- `docker stack deploy` com o **mesmo** `STACK_NAME` **atualiza** o serviço existente (não cria stack paralela).
- O ID da task muda no rolling update — isso **não é bug**; o hostname template permanece estável por nó (`inventario-gtn-python-app-01`, etc.).
- O Portainer pode mostrar uma task nova e outra `Shutdown` durante o update — é o rolling update funcionando.
- `docker stack ps` acumula histórico (`Shutdown`, `Rejected` de deploys antigos) — **não** indica excesso de containers ativos; validar só tasks `desired-state=running`.
- Com porta `mode: host`, o update deve ser **`stop-first`**; `start-first` provoca rollback por porta em uso (seção 3 e 5.3).

### Proibido

- Criar stack nova no Portainer a cada deploy.
- Mudar `STACK_NAME` entre deploys.
- Usar `docker run` para serviços de produção no cluster.

### Diagnóstico

```bash
docker stack ls                    # deve listar UMA entrada por aplicação
docker service ps inventario_gtn_web --no-trunc
```

Tasks `Running` substituindo `Shutdown` no mesmo serviço = deploy correto. Duas stacks com nomes diferentes = erro de configuração.

---

## 5.2 Porta da aplicação (obrigatório perguntar)

O cluster hospeda **várias aplicações** no mesmo modo `host`. **Não assumir porta padrão** (`8000` para Django, `8010` para FastAPI, etc.).

### Regra para o Cursor

**Antes** de gerar ou alterar `Dockerfile`, `deploy/stack.yml`, healthcheck ou backend HAProxy, **perguntar ao usuário qual porta host será usada**.

Registrar a porta escolhida em:

- variável `APP_PORT` no `.env` do servidor (`/opt/envs/minha-app.env`) e em `.env.example`;
- `deploy/stack.yml` (`command`, `ports`, `healthcheck`);
- `Dockerfile` (`EXPOSE` e bind do Gunicorn);
- configuração HAProxy do backend.

Manter controle das portas já em uso no cluster para evitar conflito em `mode: host`.

**Referência:** Inventario GTN usa `APP_PORT=8000` (escolha explícita do time, não padrão genérico).

Exemplo de variável no `.env`:

```env
APP_PORT=8000
```

---

## 5.3 Inventario GTN — padrão validado em produção

Configuração confirmada no cluster `python-app-01/02/03` (Jun/2026). Usar como referência para novas apps Django no mesmo Swarm.

| Item | Valor / decisão |
|------|-----------------|
| `STACK_NAME` | `inventario_gtn` |
| Serviço | `inventario_gtn_web` |
| `APP_PORT` | `8000` (`mode: host`) |
| Réplicas | `3` (`max_replicas_per_node: 1`) |
| Rolling update | `parallelism: 1`, **`order: stop-first`** (obrigatório com host port) |
| Imagem | `ghcr.io/c-trends-bpo/inventario:${GITHUB_SHA}` |
| Env no servidor | `/opt/envs/inventario-gtn.env` |
| Runner | `python-app-01`, labels `self-hosted`, `linux`, `swarm` |
| HAProxy backend | `192.168.0.223/224/225:8000`, path completo `/inventario/...` |
| Domínio | `www.centralretencao.com.br` |

### Scripts operacionais (`deploy/scripts/`)

```text
fix-inventario-gtn-allowed-hosts.sh   — corrige typo ALLOWED_HOSTS no .env e força service update
force-inventario-gtn-image-rollout.sh — alinha 3/3 na mesma tag (manager + stop-first)
```

Executar scripts **no manager** (`python-app-01`), com `docker login ghcr.io` ativo quando necessário.

### Checklist pós-deploy (sucesso)

```bash
docker service ls | grep inventario_gtn_web          # 3/3
docker service ps inventario_gtn_web \
  --filter "desired-state=running" \
  --format '{{.Node}} {{.Image}}'                    # uma única tag SHA
curl -fsS -H 'Host: www.centralretencao.com.br' \
  http://192.168.0.223:8000/health/                  # 200 em cada nó (.224, .225)
```

Histórico longo em `docker stack ps` (tasks `Shutdown`, `Rejected` antigas) é **normal** — só importam as 3 tasks `Running` com a mesma imagem.

### Problemas já encontrados e soluções

| Sintoma | Solução |
|---------|---------|
| 404 Django em `/inventario/login/` via HAProxy | Não remover prefixo `/inventario` no HAProxy |
| HTML não muda após deploy | `CACHE_BUST` no build; validar mesma tag nas 3 réplicas |
| `Rejected` / `No such image` | `docker pull` no workflow; GHCR internal; `--with-registry-auth` |
| `host-mode port already in use` + rollback | `stop-first` (nunca `start-first` com `mode: host`) |
| Réplicas com tags diferentes | `force-inventario-gtn-image-rollout.sh <sha>` no manager |
| Actions falha no wait com app no ar | Timeout 600s; validar tag única; re-run se `3/3` já estável |

Documentação operacional detalhada: `docs/deploy_inventario_gtn_servidor.md`.

---

# 6. Portainer

O Portainer Server está em outro servidor, fora dos nós do Swarm.

O Portainer Agent foi instalado no Swarm como serviço global.

## Rede do Agent

```bash
docker network create \
  --driver overlay \
  portainer_agent_network
```

## Serviço do Agent

```bash
docker service create \
  --name portainer_agent \
  --network portainer_agent_network \
  -p 9001:9001/tcp \
  --mode global \
  --constraint 'node.platform.os == linux' \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  --mount type=bind,src=/var/lib/docker/volumes,dst=/var/lib/docker/volumes \
  portainer/agent:lts
```

## Endereço no Portainer

O ambiente foi adicionado no Portainer como Docker Swarm via Agent.

```text
Environment name: Python Apps Swarm
Environment address: 192.168.0.223:9001
```

Observação:

- Não adicionar os 3 servidores separadamente no Portainer.
- Adicionar apenas o ambiente Swarm uma vez.
- Quando um novo nó entra no Swarm, o Agent sobe automaticamente nele por estar em modo `global`.
- Se o Agent não subir no novo nó, usar:

```bash
docker service update --force portainer_agent
```

---

# 7. Estratégia de deploy

A origem oficial do deploy deve ser o GitHub.

O Portainer deve ser usado para:

- visualizar stacks;
- visualizar serviços;
- visualizar containers;
- acompanhar logs;
- validar distribuição das réplicas;
- reiniciar serviços em caso de necessidade operacional.

Evitar editar a stack manualmente pelo Portainer, pois o próximo deploy via GitHub Actions poderá sobrescrever alterações manuais.

Fluxo desejado:

```text
Push na branch main
        ↓
GitHub Actions Self-hosted Runner
        ↓
Build da imagem Docker
        ↓
Push da imagem para GHCR ou Registry privado
        ↓
docker pull (manager) + verificação do conteúdo da imagem
        ↓
Migrations (container one-shot)
        ↓
docker stack deploy no Swarm
        ↓
Wait for replicas (3/3, mesma tag SHA, timeout 600s)
        ↓
Portainer exibe o estado da stack
        ↓
HAProxy balanceia o tráfego
```

---

# 8. GitHub Actions Self-hosted Runner

Será usado GitHub Actions com runner self-hosted.

O runner deve rodar em um nó Manager do Swarm, preferencialmente:

```text
python-app-01
```

Motivo:

- O comando `docker stack deploy` precisa ser executado em um manager do Swarm.
- O runner precisa ter acesso ao Docker local.
- O runner precisa conseguir executar `docker node ls`, `docker service ls` e `docker stack deploy`.

Labels recomendadas para o runner:

```text
self-hosted
linux
swarm
python-app
deploy
```

No workflow, usar:

```yaml
runs-on: [self-hosted, linux, swarm]
```

---

# 9. Estrutura recomendada no repositório da aplicação

Adaptar o projeto para conter:

```text
projeto/
├── Dockerfile
├── requirements.txt
├── .editorconfig
├── .gitattributes
├── .dockerignore
├── .env.example
├── deploy/
│   ├── stack.yml
│   └── scripts/
│       ├── fix-inventario-gtn-allowed-hosts.sh
│       └── force-inventario-gtn-image-rollout.sh
└── .github/
    └── workflows/
        └── deploy-swarm.yml
```

**Encoding de `requirements.txt`:** o arquivo deve estar em **UTF-8** (nunca UTF-16). Pip, Docker e Dependabot não interpretam UTF-16; sintoma típico: `Invalid requirement` na linha 1 ou Dependabot `dependency_file_not_evaluatable`. Verificação rápida: `python -c "print(open('requirements.txt','rb').read(4))"` — não deve haver `\x00` entre letras (ex.: `b'anyi'` e não `b'a\x00n\x00'`). Usar `.editorconfig` e `.gitattributes` para forçar UTF-8 e LF.

Para Django, também garantir:

```text
static/
media/
manage.py
config/
```

Para FastAPI, garantir:

```text
main.py
app/
```

---

# 10. Variáveis de ambiente

Nunca commitar `.env` real no GitHub.

No GitHub, manter somente:

```text
.env.example
```

O `.env` real deve ficar no servidor, por exemplo:

```text
/opt/envs/minha-app.env
```

Permissões recomendadas:

```bash
sudo chmod 600 /opt/envs/minha-app.env
sudo chown root:root /opt/envs/minha-app.env
```

Exemplo de `.env.example` para Django:

```env
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
SECRET_KEY=
APP_PORT=
ALLOWED_HOSTS=localhost,127.0.0.1,www.centralretencao.com.br,192.168.0.223,192.168.0.224,192.168.0.225
CSRF_TRUSTED_ORIGINS=
DATABASE_URL=
REDIS_URL=
OTEL_APPEND_IP_SUFFIX=False
```

Exemplo de `.env.example` para FastAPI:

```env
APP_ENV=production
APP_PORT=
DATABASE_URL=
REDIS_URL=
SECRET_KEY=
ALLOWED_ORIGINS=
OTEL_APPEND_IP_SUFFIX=False
```

---

# 11. Health check obrigatório

Toda aplicação deve ter endpoint de health check.

## Django

Criar endpoint:

```text
/health/
```

Resposta esperada:

```json
{"status": "ok"}
```

Status HTTP esperado:

```text
200 OK
```

O endpoint deve ser leve e não deve executar consultas pesadas.

Pode validar apenas se a aplicação está viva.

**Django + Swarm:** o `SecurityMiddleware` valida o header `Host` antes da view. Incluir `localhost,127.0.0.1` em `ALLOWED_HOSTS` **ou** configurar o healthcheck do stack com IP loopback e header `Host` do domínio de produção (ex.: `curl -fsS -H 'Host: www.exemplo.com.br' http://127.0.0.1:$${APP_PORT}/health/`). Sem isso, o healthcheck retorna `400 DisallowedHost` e o Swarm encerra a task após ~2 minutos.

## FastAPI

Criar endpoint:

```text
/health
```

Resposta esperada:

```json
{"status": "ok"}
```

Status HTTP esperado:

```text
200 OK
```

---

# 12. Dockerfile base para Django

Ajustar nomes conforme o projeto.

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Invalida cache do BuildKit no runner self-hosted a cada commit (evita COPY . . stale).
ARG CACHE_BUST
RUN test -n "${CACHE_BUST}"

COPY . .

# APP_PORT: definir após perguntar ao usuário (seção 5.2). Inventario GTN usa 8000.
ARG APP_PORT=8000
EXPOSE ${APP_PORT}

CMD ["sh", "-c", "gunicorn setup.wsgi:application --bind 0.0.0.0:${APP_PORT} --workers 4 --threads 2 --timeout 60 --max-requests 1000 --max-requests-jitter 100"]
```

Atenção:

- Trocar `setup.wsgi:application` pelo módulo WSGI correto do projeto (neste repositório: `setup.wsgi`).
- **Perguntar `APP_PORT`** antes de criar o Dockerfile (seção 5.2).
- Em produção no Swarm, a porta efetiva vem do `command` em `deploy/stack.yml` (sobrescreve o `CMD`).
- Garantir que `gunicorn` esteja no `requirements.txt`.
- Garantir que `requirements.txt` esteja em **UTF-8**; encoding UTF-16 quebra o `pip install` no build da imagem.
- Garantir que `curl` exista no container para o healthcheck.
- Em runner **self-hosted**, usar `ARG CACHE_BUST` + `build-args: CACHE_BUST=${{ github.sha }}` no workflow — sem isso, o layer `COPY . .` pode reutilizar cache local e **templates/HTML antigos** entram na imagem mesmo com commit novo (seção 17).

---

# 13. Dockerfile base para FastAPI

Ajustar nomes conforme o projeto.

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# APP_PORT: definir após perguntar ao usuário (seção 5.2).
ARG APP_PORT=8010
EXPOSE ${APP_PORT}

CMD ["sh", "-c", "gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${APP_PORT} --workers 4 --timeout 60"]
```

Atenção:

- Trocar `main:app` pelo módulo correto da aplicação.
- **Perguntar `APP_PORT`** antes de criar o Dockerfile (seção 5.2).
- Garantir que `gunicorn` e `uvicorn` estejam no `requirements.txt`.
- Garantir que `curl` exista no container para o healthcheck.

---

# 14. .dockerignore recomendado

Criar `.dockerignore`:

```dockerignore
.git
.github
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.env
.env.*
venv
.venv
node_modules
dist
build
*.sqlite3
media
staticfiles
.coverage
.pytest_cache
.mypy_cache
.idea
.vscode
```

Observação:

- Para Django, não ignorar arquivos necessários de static source.
- Ignorar apenas `staticfiles` gerado por `collectstatic`.

---

# 15. Stack base para Django (Inventario GTN)

Criar:

```text
deploy/stack.yml
```

O serviço **deve** declarar `command` com Gunicorn para manter o processo da aplicação no ar no Swarm (o `CMD` do Dockerfile sozinho pode ser omitido ou sobrescrito pelo deploy).

Exemplo alinhado ao projeto **Inventario** (`setup.wsgi:application`):

```yaml
version: "3.8"

services:
  web:
    image: ${IMAGE}

    hostname: "inventario-gtn-{{.Node.Hostname}}"

    command: >
      gunicorn setup.wsgi:application
      --bind 0.0.0.0:${APP_PORT}
      --workers 4
      --threads 2
      --timeout 60
      --max-requests 1000
      --max-requests-jitter 100

    ports:
      - target: ${APP_PORT}
        published: ${APP_PORT}
        protocol: tcp
        mode: host

    networks:
      - app_network

    environment:
      APP_PORT: ${APP_PORT}
      DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE}
      DEBUG: ${DEBUG}
      SECRET_KEY: ${SECRET_KEY}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS}
      DB_NAME: ${DB_NAME}
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_HOST: ${DB_HOST}
      DB_PORT: ${DB_PORT}
      INVENTARIO_API_BASE_URL: ${INVENTARIO_API_BASE_URL}
      TYPE_NAME: ${TYPE_NAME}
      ENABLE_TEST_ROUTES: ${ENABLE_TEST_ROUTES}
      OTEL_ENABLED: ${OTEL_ENABLED}
      OTEL_APPEND_IP_SUFFIX: ${OTEL_APPEND_IP_SUFFIX}
      OTEL_EXPORTER_OTLP_ENDPOINT: ${OTEL_EXPORTER_OTLP_ENDPOINT}
      LOKI_URL: ${LOKI_URL}
      LOG_LEVEL: ${LOG_LEVEL}

    deploy:
      mode: replicated
      replicas: 3

      placement:
        max_replicas_per_node: 1

      restart_policy:
        condition: on-failure
        delay: 5s

      update_config:
        parallelism: 1
        delay: 10s
        order: stop-first
        failure_action: rollback

      rollback_config:
        parallelism: 1
        delay: 10s
        order: stop-first

      resources:
        reservations:
          cpus: "0.50"
          memory: 512M
        limits:
          cpus: "2.00"
          memory: 2048M

    healthcheck:
      test: ["CMD-SHELL", "curl -fsS -H 'Host: www.centralretencao.com.br' http://127.0.0.1:$${APP_PORT}/health/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  app_network:
    external: true
```

Em outros projetos Django, trocar `setup.wsgi:application` pelo módulo WSGI correto (ex.: `config.wsgi:application`). Ajustar `hostname` e `APP_PORT` conforme a aplicação. Inventario GTN usa `APP_PORT=8000`.

---

# 16. Stack base para FastAPI

Criar:

```text
deploy/stack.yml
```

Exemplo:

```yaml
version: "3.8"

services:
  web:
    image: ${IMAGE}

    hostname: "minha-api-{{.Node.Hostname}}"

    command: >
      gunicorn main:app
      -k uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:${APP_PORT}
      --workers 4
      --timeout 60

    ports:
      - target: ${APP_PORT}
        published: ${APP_PORT}
        protocol: tcp
        mode: host

    networks:
      - app_network

    environment:
      APP_PORT: ${APP_PORT}
      APP_ENV: ${APP_ENV}
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      SECRET_KEY: ${SECRET_KEY}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
      OTEL_APPEND_IP_SUFFIX: ${OTEL_APPEND_IP_SUFFIX}

    deploy:
      mode: replicated
      replicas: 3

      placement:
        max_replicas_per_node: 1

      restart_policy:
        condition: on-failure
        delay: 5s

      update_config:
        parallelism: 1
        delay: 10s
        order: stop-first
        failure_action: rollback

      rollback_config:
        parallelism: 1
        delay: 10s
        order: stop-first

      resources:
        reservations:
          cpus: "0.50"
          memory: 512M
        limits:
          cpus: "2.00"
          memory: 2048M

    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:$${APP_PORT}/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  app_network:
    external: true
```

Ajustar `main:app`, `hostname` e `APP_PORT` conforme o projeto. **Perguntar a porta** antes de definir (seção 5.2).

---

# 17. GitHub Actions - workflow base

Criar:

```text
.github/workflows/deploy-swarm.yml
```

Exemplo:

```yaml
name: Build and Deploy to Docker Swarm

on:
  push:
    branches:
      - main

env:
  STACK_NAME: minha_app
  STACK_FILE: deploy/stack.yml
  ENV_FILE: /opt/envs/minha-app.env

jobs:
  deploy:
    runs-on: [self-hosted, linux, swarm]

    permissions:
      contents: read
      packages: write

    concurrency:
      group: deploy-main
      cancel-in-progress: false

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Define image name
        run: |
          IMAGE_NAME=$(echo "${GITHUB_REPOSITORY}" | tr '[:upper:]' '[:lower:]')
          echo "IMAGE=ghcr.io/${IMAGE_NAME}:${GITHUB_SHA}" >> $GITHUB_ENV
          echo "IMAGE_LATEST=ghcr.io/${IMAGE_NAME}:latest" >> $GITHUB_ENV

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          build-args: |
            CACHE_BUST=${{ github.sha }}
          tags: |
            ${{ env.IMAGE }}
            ${{ env.IMAGE_LATEST }}

      - name: Pull image on runner
        run: |
          docker pull "${IMAGE}"
          docker pull "${IMAGE_LATEST}"

      - name: Verify image tag and template layer
        run: |
          # Confirma que a imagem no registry contém o código do commit (ex.: trecho de index.html)
          # Ver implementação em .github/workflows/deploy-swarm.yml

      - name: Validate Swarm cluster
        run: |
          docker node ls
          docker network ls | grep app_network

      - name: Run database migrations
        run: |
          docker run --rm \
            --env-file "${ENV_FILE}" \
            "${IMAGE}" \
            python manage.py migrate --noinput

      - name: Validate and fix environment file
        run: |
          # Valida APP_PORT e ALLOWED_HOSTS; corrige typo ALLOWED_HOSTS=ALLOWED_HOSTS=...
          # Ver implementação em .github/workflows/deploy-swarm.yml

      - name: Deploy stack
        run: |
          set -a
          source "${ENV_FILE}"
          set +a
          export IMAGE="${IMAGE}"

          docker pull "${IMAGE}"

          docker stack deploy \
            --with-registry-auth \
            -c "${STACK_FILE}" \
            "${STACK_NAME}"

          docker service inspect "${STACK_NAME}_web" --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'

      - name: Wait for replicas
        run: |
          # Aguarda 3/3 réplicas estáveis antes de concluir o job.
          # Parâmetros recomendados (Inventario GTN):
          #   TIMEOUT=600        — rolling update com healthcheck start_period 40s pode passar de 5 min
          #   INTERVAL=15        — intervalo entre checagens
          #   STABLE_REQUIRED=2  — exige 2 leituras consecutivas OK (evita falso positivo no meio do update)
          #
          # Critérios de sucesso:
          #   docker service ls → inventario_gtn_web 3/3
          #   docker service ps → 3 tasks Running na MESMA tag (${GITHUB_SHA})
          #
          # Ver implementação completa em .github/workflows/deploy-swarm.yml
```

Ajustar:

```yaml
STACK_NAME: minha_app
ENV_FILE: /opt/envs/minha-app.env
```

para o nome real da aplicação.

### Passo `Wait for replicas` — parâmetros e armadilhas

Com `replicas: 3`, `parallelism: 1`, `order: stop-first` (obrigatório com **porta `mode: host`**) e healthcheck com `start_period: 40s`, o rolling update pode levar **vários minutos** até `3/3` na mesma tag. Timeout de **300s é curto** — usar **600s** (10 min).

| Parâmetro | Valor recomendado | Motivo |
|-----------|-------------------|--------|
| `TIMEOUT` | `600` | 3 réplicas × (start_period + checks) + delays entre updates |
| `INTERVAL` | `15` | Polling sem sobrecarregar o manager |
| `STABLE_REQUIRED` | `2` | Duas leituras consecutivas `3/3` evitam sucesso prematuro no meio do rolling |

**Contagem confiável:** não usar só `docker service ls --filter name=... | head -1` (filtro por substring e `head -1` são frágeis). Preferir:

- `docker service ls --format '{{.Name}} {{.Replicas}}' | awk '$1 == svc'`
- `docker service ps` contando tasks com `CurrentState` = `Running`
- **Mesma tag** em todas as tasks Running (`count` de imagens com o SHA do commit = 3)

**Rollback `host-mode port already in use`:** ocorre com `start-first` + porta `mode: host`. O Swarm desfaz o update (`rollback: update rolled back`). Corrigir `deploy/stack.yml` para `stop-first` e rodar `force-inventario-gtn-image-rollout.sh` no manager — **não** usar `start-first` em `docker service update` manual.

**Falso negativo no Actions:** o job pode falhar em `Wait for replicas` mesmo com a aplicação já respondendo via HAProxy — o `docker stack deploy` já aplicou a stack; validar com `docker service ls | grep <stack>` no servidor. Re-run do workflow ou aguardar estabilização costuma resolver.

**Réplicas em tags diferentes (HTML “às vezes muda”):** se `docker service ps ... --format '{{.Image}}'` listar **mais de uma tag** entre tasks `Running`, o rolling update não terminou — HAProxy alterna nó antigo/novo. O wait do workflow exige **3/3 na mesma tag** do commit. Correção manual no **manager**:

```bash
bash deploy/scripts/force-inventario-gtn-image-rollout.sh <sha-do-commit>
```

O script usa `--update-order stop-first` e `--with-registry-auth`.

**Referência:** `.github/workflows/deploy-swarm.yml` (Inventario GTN).

### `docker pull` antes do deploy

Após `build-push`, executar `docker pull` da tag `${GITHUB_SHA}` no manager (runner):

- Confirma que a imagem está no registry antes de `docker run` (migrations) e `stack deploy`.
- Reduz tasks `Rejected` com `No such image` nos nós do Swarm.
- Repetir `docker pull` imediatamente antes do `stack deploy` (credenciais GHCR ainda ativas no job).

Os workers puxam a imagem na criação da task via `--with-registry-auth`. O pull no manager **não** substitui auth nos nós — garantir pacote GHCR com permissão de pull (seção 18).

### Alteração em HTML/template não aparece após deploy OK

**Não é cache do Django** (não há `CACHES` de template em produção). Causas frequentes:

| Causa | Como detectar |
|-------|----------------|
| Cache de build no runner self-hosted (`COPY . .` stale) | Log do build muito rápido; `Verify image tag` no Actions mostra HTML antigo |
| Imagem errada nas réplicas | `docker service ps inventario_gtn_web --filter desired-state=running --format '{{.Image}}'` ≠ commit esperado |
| Browser | Aba anônima / hard refresh |
| Arquivo em `static/` (excluído do `.dockerignore` na raiz) | Mudança em CSS não entra no `collectstatic` do build |

**Diagnóstico no servidor:**

```bash
docker service ps inventario_gtn_web --filter "desired-state=running" --format '{{.Node}} {{.Image}}'
docker exec $(docker ps -q --filter "name=inventario_gtn_web" | head -1) \
  head -20 /app/inventario/templates/inventario/index.html
```

Se o `cat`/`head` no container mostrar HTML antigo, o problema é **build/imagem**, não HAProxy nem browser.

**Prevenção:** `ARG CACHE_BUST` no `Dockerfile` + `build-args: CACHE_BUST=${{ github.sha }}` no workflow (Inventario GTN).

---

# 18. Autenticação no GHCR

## Abordagem preferida: `GITHUB_TOKEN`

Na fase inicial, **não** criar secrets `GHCR_USER` e `GHCR_PAT`.

O workflow já declara:

```yaml
permissions:
  contents: read
  packages: write
```

O login no registry usa o token automático do job:

```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

Requisitos:

- `packages: write` no job (ou no workflow) para publicar imagens no GHCR.
- `docker stack deploy --with-registry-auth` repassa as credenciais do runner ao Swarm para pull nos nós.
- Pacote GHCR com visibilidade compatível com o repositório (interno ou vinculado ao repo).
- Se workers falharem com `No such image` em deploy manual fora do Actions: executar `docker login ghcr.io` uma vez em cada nó (`python-app-01/02/03`) ou usar PAT com `read:packages`.

## Fallback: PAT dedicado (opcional)

Criar secrets no repositório somente se `GITHUB_TOKEN` não atender:

```text
Settings > Secrets and variables > Actions > New repository secret
```

```text
GHCR_USER
GHCR_PAT
```

Casos típicos: pacote em outra org, pull cross-repo, ou token de longa duração fora do ciclo do workflow.

No login, trocar para:

```yaml
username: ${{ secrets.GHCR_USER }}
password: ${{ secrets.GHCR_PAT }}
```

---

# 19. Comandos úteis no Swarm

Executar em um manager, preferencialmente `python-app-01`.

## Ver nós

```bash
docker node ls
```

## Ver serviços

```bash
docker service ls
```

## Ver stacks

```bash
docker stack ls
```

## Ver serviços de uma stack

```bash
docker stack services minha_app
```

## Ver tasks de uma stack

```bash
docker stack ps minha_app --no-trunc
```

## Ver logs de um serviço

```bash
docker service logs -f minha_app_web
```

## Forçar rollout de imagem (réplicas em tags diferentes)

No manager, preferir o script do repositório em vez de `docker service update --force` genérico:

```bash
bash deploy/scripts/force-inventario-gtn-image-rollout.sh <sha-do-commit>
```

## Validar réplicas após deploy (ou Actions com wait falho)

```bash
docker service ls --format 'table {{.Name}}\t{{.Replicas}}' | grep inventario_gtn
docker service ps inventario_gtn_web \
  --filter "desired-state=running" \
  --format '{{.Node}} {{.Image}}'
docker service logs inventario_gtn_web --tail 50
```

Esperado: **3 linhas**, **uma única tag** `ghcr.io/c-trends-bpo/inventario:<sha>`.

Se `3/3` mas o workflow falhou em `Wait for replicas`, o deploy já foi aplicado — ver seção 17 (falso negativo por timeout ou polling).

## Remover stack

```bash
docker stack rm minha_app
```

---

# 20. HAProxy - exemplos

## Regra crítica — não remover prefixo de path

O HAProxy deve encaminhar o **path completo** recebido do cliente para o backend. **Não** usar `http-request set-path`, `reqrep` ou ACL que remova prefixos como `/inventario`.

Exemplo do problema (Inventario GTN):

```text
Cliente  → GET /inventario/login/
HAProxy  → GET /login/          ← strip incorreto
Django   → 404 (rota só existe em /inventario/login/)
```

O 404 exibido é o **template padrão do Django** (`Server: gunicorn`), não página de erro do HAProxy.

**Diagnóstico rápido:**

```bash
# Deve retornar 200 — container OK
curl -I http://192.168.0.223:8000/inventario/login/ -H "Host: www.centralretencao.com.br"

# Se falhar aqui mas OK acima → problema no HAProxy (path ou backend errado)
curl -I http://<haproxy>:<porta>/inventario/login/ -H "Host: www.centralretencao.com.br"
```

No Django, `LOGIN_URL` / `LOGOUT_REDIRECT_URL` devem usar o mesmo prefixo das URLs (`/inventario/login/`, não `/login/` na raiz).

## Django

Substituir `${APP_PORT}` pela porta escolhida para a aplicação (seção 5.2). Inventario GTN usa `8000`.

```haproxy
backend minha_app_django
    balance roundrobin
    option httpchk GET /health/
    http-check expect status 200-399

    server python-app-01 192.168.0.223:${APP_PORT} check
    server python-app-02 192.168.0.224:${APP_PORT} check
    server python-app-03 192.168.0.225:${APP_PORT} check
```

## FastAPI

```haproxy
backend minha_app_fastapi
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200-399

    server python-app-01 192.168.0.223:${APP_PORT} check
    server python-app-02 192.168.0.224:${APP_PORT} check
    server python-app-03 192.168.0.225:${APP_PORT} check
```

---

# 21. Regras importantes para o Cursor aplicar no projeto

Ao adaptar o projeto, o Cursor deve:

1. Identificar se o projeto é Django ou FastAPI.
2. Criar ou ajustar `Dockerfile`.
3. Criar `.dockerignore`.
4. Criar `.env.example`, sem valores reais.
5. Criar `deploy/stack.yml`.
6. Criar `.github/workflows/deploy-swarm.yml`.
7. Adicionar dependências necessárias no `requirements.txt` (sempre **UTF-8**, fim de linha LF; evitar salvar como UTF-16 no Windows).
8. Garantir que exista endpoint `/health/` para Django ou `/health` para FastAPI.
9. Garantir que Gunicorn esteja configurado no `Dockerfile` **e** no `command` de `deploy/stack.yml`.
10. Não commitar `.env` real.
11. Não salvar uploads dentro do container.
12. Não usar banco de dados dentro do container da aplicação.
13. Não colocar Redis dentro do container da aplicação.
14. **Perguntar `APP_PORT` ao usuário** antes de criar `Dockerfile`, `deploy/stack.yml`, healthcheck ou backend HAProxy — não assumir porta padrão (seção 5.2).
15. Usar `STACK_NAME` fixo no workflow e `hostname` com template `{{.Node.Hostname}}` na stack (seção 5.1).
16. Nunca criar stack duplicada no Portainer; sempre `docker stack deploy` com o mesmo `STACK_NAME`.
17. Usar `mode: host` nas portas publicadas.
18. Usar `max_replicas_per_node: 1`.
19. Usar `app_network` como rede externa.
20. Garantir que logs saiam em stdout/stderr para Docker/Portainer/Loki.
21. No Swarm, definir `OTEL_APPEND_IP_SUFFIX=False` no `.env` do servidor (seção 22).
22. Ajustar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` e CORS conforme domínio real. **Sempre incluir `localhost,127.0.0.1`** no início de `ALLOWED_HOSTS` para healthchecks Docker/HAProxy internos; evitar typo `ALLOWED_HOSTS=ALLOWED_HOSTS=...`.
23. Validar que o projeto inicia sem depender de arquivos locais não versionados.
24. No workflow de deploy, incluir passo **Wait for replicas** com timeout **≥ 600s** e validação de **mesma tag** nas 3 réplicas (seção 17).
25. Com porta **`mode: host`**, usar `update_config.order: stop-first` — `start-first` causa `host-mode port already in use` (seção 15 / stack).
26. Após `build-push`, executar **`docker pull`** da tag do commit antes de migrations e `stack deploy` (seção 17).
27. Em runner self-hosted, usar **`CACHE_BUST=${{ github.sha }}`** no build para não reutilizar layer `COPY . .` com código antigo (seção 12 e 17).
28. No HAProxy, **não remover prefixo de path** ao encaminhar para Django montado em subpath (ex.: `/inventario/`); alinhar `LOGIN_URL` com o prefixo real (seção 20).
29. Manter scripts em `deploy/scripts/` para correções operacionais recorrentes (ALLOWED_HOSTS, rollout de imagem) — ver seção 5.3.

---

# 22. Observabilidade

A infra existente possui observabilidade com:

```text
Grafana
Prometheus
Loki
Tempo
cAdvisor
node-exporter
HAProxy metrics
```

As aplicações devem preferencialmente:

- logar em stdout/stderr;
- usar logs estruturados quando possível;
- expor endpoint `/metrics` se houver instrumentação Prometheus;
- manter endpoint `/health` ou `/health/`;
- incluir OpenTelemetry quando o projeto já tiver padrão configurado;
- não gravar logs apenas em arquivo local dentro do container.

## Padrão no Docker Swarm

No `.env` do servidor (`/opt/envs/minha-app.env`), incluir:

```env
OTEL_ENABLED=True
OTEL_APPEND_ENV=True
OTEL_APPEND_IP_SUFFIX=False
OTEL_EXPORTER_OTLP_ENDPOINT=http://192.168.0.213:4318
LOKI_URL=http://192.168.0.213:3100/loki/api/v1/push
LOG_LEVEL=INFO
```

Repassar `OTEL_APPEND_IP_SUFFIX` no `environment` de `deploy/stack.yml`.

### Nome da aplicação em Loki/Tempo

Com `OTEL_APPEND_IP_SUFFIX=False`, o nome enviado fica **sem octeto de IP**:

```text
<base>-<ambiente>
```

Exemplo Inventario GTN em produção:

```text
Inventario GTN-producao
```

**Não** usar sufixo de IP no nome do app (`Inventario GTN-producao-223` é indesejado no Swarm). Várias réplicas compartilham o mesmo nome de serviço nos logs; a tag `host` do Loki (IP ou hostname do nó) distingue a instância quando necessário.

### Consulta no Loki

```logql
{app="Inventario GTN-producao"}
```

Em dev local, `OTEL_APPEND_IP_SUFFIX=True` pode permanecer para distinguir máquinas de desenvolvimento.

---

# 23. Cuidados com arquivos e uploads

Como a aplicação roda em múltiplas réplicas, não salvar arquivos importantes localmente dentro do container.

Evitar:

```text
/app/media
/tmp definitivo
arquivos de usuário dentro do container
uploads no disco local da VM
```

Usar uma das opções:

```text
MinIO
S3
NFS/storage compartilhado
servidor de arquivos central
```

---

# 24. Banco e Redis

Banco e Redis devem estar fora dos containers da aplicação.

As aplicações devem acessar:

```text
DATABASE_URL
REDIS_URL
```

via variáveis de ambiente.

---

# 25. Resumo final da arquitetura

```text
GitHub
  ↓ push main
GitHub Actions Self-hosted Runner no python-app-01
  ↓ build
GitHub Container Registry
  ↓ docker stack deploy
Docker Swarm
  ├── python-app-01
  ├── python-app-02
  └── python-app-03
  ↓
Containers Django/FastAPI
  ↓
HAProxy
  ↓
Usuários e sistemas externos
```

