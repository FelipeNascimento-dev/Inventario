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
  - target: 8000
    published: 8000
    protocol: tcp
    mode: host
```

Motivo:

- O HAProxy consegue checar diretamente cada servidor.
- A porta só fica aberta no servidor onde o container está rodando.
- O health check do HAProxy fica mais confiável.
- Evita dupla camada de balanceamento: HAProxy + ingress routing mesh.

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
docker stack deploy no Swarm
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
│   └── stack.yml
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
DATABASE_URL=
ALLOWED_HOSTS=
CSRF_TRUSTED_ORIGINS=
REDIS_URL=
```

Exemplo de `.env.example` para FastAPI:

```env
APP_ENV=production
DATABASE_URL=
REDIS_URL=
SECRET_KEY=
ALLOWED_ORIGINS=
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

COPY . .

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "60", "--max-requests", "1000", "--max-requests-jitter", "100"]
```

Atenção:

- Trocar `config.wsgi:application` pelo módulo correto do projeto.
- Garantir que `gunicorn` esteja no `requirements.txt`.
- Garantir que `requirements.txt` esteja em **UTF-8**; encoding UTF-16 quebra o `pip install` no build da imagem.
- Garantir que `curl` exista no container para o healthcheck.

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

EXPOSE 8010

CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8010", "--workers", "4", "--timeout", "60"]
```

Atenção:

- Trocar `main:app` pelo módulo correto da aplicação.
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

# 15. Stack base para Django

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

    command: >
      gunicorn config.wsgi:application
      --bind 0.0.0.0:8000
      --workers 4
      --threads 2
      --timeout 60
      --max-requests 1000
      --max-requests-jitter 100

    ports:
      - target: 8000
        published: 8000
        protocol: tcp
        mode: host

    networks:
      - app_network

    environment:
      DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE}
      DEBUG: ${DEBUG}
      SECRET_KEY: ${SECRET_KEY}
      DATABASE_URL: ${DATABASE_URL}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS}
      REDIS_URL: ${REDIS_URL}

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
        order: start-first
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
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  app_network:
    external: true
```

Ajustar `config.wsgi:application` conforme o projeto.

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

    command: >
      gunicorn main:app
      -k uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8010
      --workers 4
      --timeout 60

    ports:
      - target: 8010
        published: 8010
        protocol: tcp
        mode: host

    networks:
      - app_network

    environment:
      APP_ENV: ${APP_ENV}
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      SECRET_KEY: ${SECRET_KEY}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}

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
        order: start-first
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
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  app_network:
    external: true
```

Ajustar `main:app` conforme o projeto.

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
          tags: |
            ${{ env.IMAGE }}
            ${{ env.IMAGE_LATEST }}

      - name: Validate Swarm node
        run: |
          docker node ls
          docker network ls | grep app_network

      - name: Deploy stack
        run: |
          set -a
          source "${ENV_FILE}"
          set +a

          docker stack deploy \
            --with-registry-auth \
            -c "${STACK_FILE}" \
            "${STACK_NAME}"

      - name: Check services
        run: |
          docker stack services "${STACK_NAME}"
          docker stack ps "${STACK_NAME}" --no-trunc
```

Ajustar:

```yaml
STACK_NAME: minha_app
ENV_FILE: /opt/envs/minha-app.env
```

para o nome real da aplicação.

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

## Forçar atualização de serviço

```bash
docker service update --force minha_app_web
```

## Remover stack

```bash
docker stack rm minha_app
```

---

# 20. HAProxy - exemplos

## Django

```haproxy
backend minha_app_django
    balance roundrobin
    option httpchk GET /health/
    http-check expect status 200-399

    server python-app-01 192.168.0.223:8000 check
    server python-app-02 192.168.0.224:8000 check
    server python-app-03 192.168.0.225:8000 check
```

## FastAPI

```haproxy
backend minha_app_fastapi
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200-399

    server python-app-01 192.168.0.223:8010 check
    server python-app-02 192.168.0.224:8010 check
    server python-app-03 192.168.0.225:8010 check
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
9. Garantir que Gunicorn esteja configurado corretamente.
10. Não commitar `.env` real.
11. Não salvar uploads dentro do container.
12. Não usar banco de dados dentro do container da aplicação.
13. Não colocar Redis dentro do container da aplicação.
14. Ajustar portas conforme a aplicação:
    - Django: 8000
    - FastAPI: 8010 ou porta definida para a API
15. Usar `mode: host` nas portas publicadas.
16. Usar `max_replicas_per_node: 1`.
17. Usar `app_network` como rede externa.
18. Garantir que logs saiam em stdout/stderr para Docker/Portainer/Loki.
19. Ajustar `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` e CORS conforme domínio real.
20. Validar que o projeto inicia sem depender de arquivos locais não versionados.

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

