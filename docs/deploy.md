# Деплой

Один VPS, docker-compose, Caddy впереди. Образы собирает GitHub Actions и кладёт в GHCR, VPS их скачивает.

Пуш в `main` → зелёный workflow `CI` → workflow `Deploy` (`.github/workflows/deploy.yml`):

1. собирает `ghcr.io/hhaakkimm/devplus-api` и `devplus-web` с тегом `<sha коммита>` и пушит их в GHCR;
2. копирует `infra/docker-compose.yml` и `infra/Caddyfile` в `/opt/devplus/`;
3. по SSH пишет `IMAGE_TAG=<sha>` в `/opt/devplus/.env` и выполняет `docker compose pull && docker compose up -d --wait`. Миграции запускает сервис `migrate` перед `api`.

Пока переменная репозитория `VPS_HOST` не задана, `Deploy` пропускается и `main` остаётся зелёным.

## Раскладка на сервере

```
/opt/devplus/
  docker-compose.yml   # копирует деплой
  Caddyfile            # копирует деплой
  app.env              # секреты и настройки, ты создаёшь вручную, в git его нет
  .env                 # только IMAGE_TAG=<sha>, пишет деплой
```

## Подготовка VPS

1. Поставь Docker с плагином compose ([инструкция](https://docs.docker.com/engine/install/)). Нужен Compose v2.
2. Заведи пользователя для деплоя и добавь его в группу `docker`:

   ```bash
   sudo adduser --disabled-password deploy
   sudo usermod -aG docker deploy
   sudo mkdir -p /opt/devplus && sudo chown deploy: /opt/devplus
   ```

3. Сгенерируй ключ для деплоя на своей машине и положи публичную часть в `~deploy/.ssh/authorized_keys`:

   ```bash
   ssh-keygen -t ed25519 -f devplus-deploy -N "" -C devplus-deploy
   ```

4. Войди в GHCR от имени `deploy` (классический PAT со scope `read:packages`, создаётся в GitHub → Settings → Developer settings → Personal access tokens):

   ```bash
   docker login ghcr.io -u <github-login>
   ```

5. Создай `/opt/devplus/app.env` из `infra/app.env.example` и заполни его. Пароль Postgres подставь в `DATABASE_URL` руками, `APP_ORIGIN` равен `https://<DOMAIN>`. Права: `chmod 600 /opt/devplus/app.env`.
6. DNS: A-запись `<DOMAIN>` на IP сервера. Открой порты 80 и 443: Caddy сам получит сертификат.

## Продовое OAuth-приложение GitHub

Отдельное приложение, не то, что для разработки: GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.

- Homepage URL: `https://<DOMAIN>`
- Authorization callback URL: `https://<DOMAIN>/api/auth/github/callback`

Client ID и Client secret положи в `app.env` (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).

## Настройки репозитория

GitHub → репозиторий → Settings → Secrets and variables → Actions.

| Где | Имя | Значение |
| --- | --- | --- |
| Variables | `VPS_HOST` | адрес сервера. Пока не задана, деплой пропускается |
| Variables | `VPS_USER` | пользователь для деплоя (`deploy`) |
| Secrets | `VPS_SSH_KEY` | приватный ключ из `devplus-deploy` целиком |

Пуш образов в GHCR идёт через встроенный `GITHUB_TOKEN`, отдельный секрет не нужен.

## Проверка

После пуша в `main` дождись зелёных `CI` и `Deploy`, затем:

```bash
curl https://<DOMAIN>/api/health   # {"status":"ok"}
```

## Откат

Старые образы остаются в GHCR под своими тегами, следующий деплой перезапишет `.env`. Все команды, кроме `git diff`, выполняй на сервере, в `/opt/devplus`.

Сначала проверь в клоне репозитория, менялась ли схема БД между версиями:

```bash
git diff --stat <старый-sha> <текущий-sha> -- apps/api/migrations
```

**Миграций между версиями нет.** Просто переключи тег:

```bash
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait
```

**Между версиями есть миграция.** Простое переключение тега здесь ломается. Сервис `migrate` стартует из старого образа и выполняет `alembic upgrade head`, а БД уже на ревизии, которой в старом образе нет. Он падает с `Can't locate revision`, `api` из-за `service_completed_successfully` не пересоздаётся и остаётся на новой версии, а `web` может переключиться на старую. Сначала откати схему образом **текущей** версии, потом переключай тег:

```bash
# 1. копия БД: downgrade может удалить данные
docker compose exec -T postgres pg_dump -U devplus devplus > ~/devplus-$(date +%F-%H%M).sql
# 2. ревизия старой версии (alembic читает только файлы миграций, БД не нужна)
docker run --rm ghcr.io/hhaakkimm/devplus-api:<старый-sha> alembic heads
# 3. остановить приложение и откатить схему образом текущей версии
docker compose stop api web
docker compose run --rm migrate alembic downgrade <ревизия-из-шага-2>
# 4. переключить тег
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait
```

На шаге 3 `.env` ещё содержит текущий тег, поэтому `migrate` берёт текущий образ. Если у миграции нет кода в `downgrade`, откат схемы невозможен: восстанови БД из копии шага 1.

## Добавить человека

Допиши логин в `ALLOWED_GITHUB_LOGINS` в `/opt/devplus/app.env` (через запятую) и перезапусти api:

```bash
cd /opt/devplus && docker compose up -d api
```

Убрать человека так же: его живая сессия перестанет работать с первого же запроса.
