# Production deployment

This guide describes a production deployment with Docker Compose. It is
deliberately environment-neutral so that it can remain in the public source
repository.

Keep site-specific infrastructure information—hostnames, IP addresses, SSH
inventory, firewall identifiers, backup destinations, and secret values—in a
separate private infrastructure repository or secret manager.

## Host layout

Run deployments through a dedicated, non-interactive `deploy` account. A
typical filesystem layout is:

```text
/srv/apps/just-os/          Git checkout
/srv/data/just-os/          knowledge-base data
/etc/just-os/app.env        production configuration and secrets
```

The checkout and data can be owned by `deploy:deploy`. The environment file
should be readable only by root and the deployment group, for example mode
`0640`. Do not store secret values or generated knowledge-base data in Git.

## Reverse proxy on another host

The web container binds to `127.0.0.1:8000` by default. If the reverse proxy
runs on another VM in the same private network, set the bind address to the
application VM's private address:

```dotenv
DOCKER_WEB_PORT_FORWARD=10.0.0.20:8000
```

Configure the reverse proxy to forward to that address and port. Permit TCP
port 8000 from the reverse-proxy VM only. Do not expose Redis. When using
Docker-published ports, enforce the source restriction in the cloud/network
firewall or in the host's Docker-aware firewall chain; ordinary host firewall
rules do not always filter Docker traffic.

TLS may terminate at the reverse proxy on a trusted private network. Use TLS or
mTLS between the hosts when the internal network is not fully trusted.

The production Compose override no longer assumes that a reverse proxy shares
the Docker host or an external Docker network.

## Persistent data

The application mounts `./data` read-only at runtime. On a production host,
either place the deployment data at `/srv/data/just-os` and link `data` to it,
or maintain a private Compose override that binds the absolute host path:

```yaml
services:
  web:
    volumes:
      - /srv/data/just-os:/app/data:ro
```

An explicit private override is preferable when deployment configuration is
managed as code.

The application expects the persisted vector index below the mounted data
directory. With the default configuration, the important path is:

```text
/app/data/processed/vs_latest_bge-small-en-v1.5
```

Production data is transferred and managed separately from the Git checkout.
It is not baked into the image. The `:ro` mount prevents the web application
from modifying it.

## Start and update

Copy `.env.example` to the protected production environment file, replace all
placeholder values, and set the following value inside that file so Compose
also supplies it to the container:

```dotenv
JUST_OS_ENV_FILE=/etc/just-os/app.env
```

Start a pinned, reviewed revision with:

```bash
docker compose \
  --project-name justos \
  --env-file /etc/just-os/app.env \
  -f compose.yaml \
  -f compose.prod.yaml \
  up -d --build --remove-orphans
```

Use a distinct Compose project name when other applications share the VM.
Deploy tagged releases or pinned commits rather than pulling an unreviewed
branch directly into production.

## Backups and operations

Back up the knowledge-base data, the protected environment file, and the Redis
volume if conversation state must survive a rebuild. Test restoration
regularly. Container images and build caches can be recreated and normally do
not need backup.

Monitor the `/up` health endpoint through the private network and configure
Docker log rotation at the daemon level or through a Compose logging policy.
