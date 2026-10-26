# Деплой

Один VPS, docker-compose, Caddy впереди. Образы собирает GitHub Actions и кладёт в GHCR, VPS их скачивает.

Пуш в `main` → зелёный workflow `CI` → workflow `Deploy` (`.github/workflows/deploy.yml`):

1. собирает `ghcr.io/hhaakkimm/devplus-api` и `devplus-web` с тегом `<sha коммита>` и пушит их в GHCR. Контекст сборки обоих образов: корень репозитория, в `api` попадают файлы задач Тренажёра (см. «Redis и worker»);
2. копирует `infra/docker-compose.yml` и `infra/Caddyfile` в `/opt/devplus/`;
3. по SSH пишет `IMAGE_TAG=<sha>` в `/opt/devplus/.env` и выполняет `docker compose pull && docker compose up -d --wait`. Миграции запускает сервис `migrate` перед `api` и `worker`.

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

1. Нужен сервер x86_64: образы собираются только под `linux/amd64`, на ARM они не запустятся. Поставь Docker с плагином compose ([инструкция](https://docs.docker.com/engine/install/)). Нужен Compose v2.
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

5. Создай `/opt/devplus/app.env` из `infra/app.env.example` и заполни его. Пароль Postgres подставь в `DATABASE_URL` руками, `APP_ORIGIN` равен `https://<DOMAIN>`, `ANTHROPIC_API_KEY` берётся в консоли Anthropic. Права: `chmod 600 /opt/devplus/app.env`.
6. DNS: A-запись `<DOMAIN>` на IP сервера. Открой порты 80 и 443: Caddy сам получит сертификат.

## Продовое OAuth-приложение GitHub

Отдельное приложение, не то, что для разработки: GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.

- Homepage URL: `https://<DOMAIN>`
- Authorization callback URL: `https://<DOMAIN>/api/auth/github/callback`

Client ID и Client secret положи в `app.env` (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).

## Redis и worker

Оценщик промптов гоняет прогоны в фоне:

- `redis` (`redis:7`): очередь прогонов. Порт наружу не публикуется, секретов в нём нет, тома тоже нет. Если Redis потеряет очередь, `worker` при старте ставит `queued` прогоны заново, а `running` переводит в `failed`.
- `worker`: образ `api`, команда `taskiq worker app.worker:broker --workers 1 --max-async-tasks 2`: один процесс, не больше двух прогонов одновременно. Читает тот же `app.env`, что и `api`.
- Образ `api` содержит `content/*/tasks/*.yaml` и `*.mdx` в `/app/content`: YAML со скрытыми кейсами Тренажёра читает только API. В образ `web` попадает только MDX, YAML туда не должен попасть.

Переменные в `app.env` (значения из `infra/app.env.example`):

| Имя | Значение |
| --- | --- |
| `ANTHROPIC_API_KEY` | ключ Anthropic API, нужен при `EVALS_LLM_BACKEND=anthropic` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `EVALS_LLM_BACKEND` | `anthropic`; `fake` отдаёт ответы-заглушки без обращений к API |
| `EVALS_RUN_COST_LIMIT_USD` | предельная стоимость одного прогона, по умолчанию 5 |
| `EVALS_CONCURRENCY` | сколько кейсов одного прогона идут параллельно, по умолчанию 4 |
| `CONTENT_DIR` | `/app/content` |

На уже работающем сервере допиши эти переменные в `app.env` до первого деплоя этой версии: без них `api` и `worker` возьмут настройки для разработки (`REDIS_URL=redis://localhost:6379/0`, `CONTENT_DIR=../../content`), и очередь с задачами Тренажёра не заработают. После правки `app.env` перезапусти оба сервиса: `docker compose up -d api worker`.

## Настройки репозитория

Переменные: GitHub → репозиторий → Settings → Secrets and variables → Actions → Variables (на уровне репозитория).

| Имя | Значение |
| --- | --- |
| `VPS_HOST` | адрес сервера. Пока не задана, деплой пропускается |
| `VPS_USER` | пользователь для деплоя (`deploy`) |

`VPS_HOST` обязательно держи на уровне репозитория, а не окружения: условие `if` у job вычисляется до применения окружения и не увидит переменную окружения.

Секрет: GitHub → репозиторий → Settings → Environments → New environment `production`. В Deployment branches and tags выбери Selected branches and tags и добавь правило `main`. В Environment secrets добавь `VPS_SSH_KEY` (приватный ключ из `devplus-deploy` целиком). Так ключ доступен только job деплоя на `main`, а не любому workflow репозитория.

Пуш образов в GHCR идёт через встроенный `GITHUB_TOKEN`, отдельный секрет не нужен.

## Проверка

После пуша в `main` дождись зелёных `CI` и `Deploy`, затем:

```bash
curl https://<DOMAIN>/api/health   # {"status":"ok"}
```

На сервере `docker compose ps` показывает `redis` здоровым, а `worker` запущенным.

## Откат

Старые образы остаются в GHCR под своими тегами, следующий деплой перезапишет `.env`. Все команды, кроме `git diff`, выполняй на сервере, в `/opt/devplus`. `<текущий-sha>` смотри там же: `cat /opt/devplus/.env`.

Откат на версию до оценщика промптов: в её образе нет `app.worker`, поэтому в обоих вариантах ниже при переключении тега добавляй `--scale worker=0`: `docker compose up -d --wait --scale worker=0`.

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
# 1. остановить приложение: во время копии БД никто не пишет
docker compose stop api web worker
# 2. копия БД: downgrade может удалить данные
docker compose exec -T postgres pg_dump --clean --if-exists -U devplus devplus > ~/devplus-$(date +%F-%H%M).sql
# 3. ревизия старой версии (alembic читает только файлы миграций, БД не нужна)
docker run --rm ghcr.io/hhaakkimm/devplus-api:<старый-sha> alembic heads
# 4. откатить схему образом текущей версии
docker compose run --rm migrate alembic downgrade <ревизия-из-шага-3>
# 5. переключить тег
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait
```

На шаге 4 `.env` ещё содержит текущий тег, поэтому `migrate` берёт текущий образ.

Если `downgrade` упал или стёр данные, верни БД из копии шага 2 (в ней есть `DROP ... IF EXISTS`, поэтому она ложится поверх существующей базы). `api`, `web` и `worker` при этом остаются остановленными:

```bash
docker compose exec -T postgres psql -U devplus devplus < ~/devplus-<дата>.sql
```

Если у миграции нет кода в `downgrade`, откат схемы невозможен: исправляй вперёд новым коммитом.

## Добавить человека

Допиши логин в `ALLOWED_GITHUB_LOGINS` в `/opt/devplus/app.env` (через запятую) и перезапусти api:

```bash
cd /opt/devplus && docker compose up -d api
```

Убрать человека так же: его живая сессия перестанет работать с первого же запроса.
