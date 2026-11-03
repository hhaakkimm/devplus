# Деплой

Один VPS, docker-compose, Caddy впереди. Образы собирает GitHub Actions и кладёт в GHCR, VPS их скачивает.

Пуш в `main` → зелёный workflow `CI` → workflow `Deploy` (`.github/workflows/deploy.yml`):

1. собирает `ghcr.io/hhaakkimm/devplus-api`, `devplus-web` и `devplus-backup` с тегом `<sha коммита>` и пушит их в GHCR. Контекст сборки `api` и `web`: корень репозитория, в `api` попадают файлы задач Тренажёра (см. «Redis и worker»). Контекст `backup`: `infra/backup`;
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

5. Создай `/opt/devplus/app.env` из `infra/app.env.example` и заполни его. Пароль Postgres подставь в `DATABASE_URL` руками, `APP_ORIGIN` равен `https://<DOMAIN>`, `ANTHROPIC_API_KEY` берётся в консоли Anthropic. Значения `BACKUP_S3_*` см. в разделе «Бэкапы». Права: `chmod 600 /opt/devplus/app.env`.
6. DNS: A-запись `<DOMAIN>` на IP сервера. Открой порты 80 и 443: Caddy сам получит сертификат.

## Продовое OAuth-приложение GitHub

Отдельное приложение, не то, что для разработки: GitHub → Settings → Developer settings → OAuth Apps → New OAuth App.

- Homepage URL: `https://<DOMAIN>`
- Authorization callback URL: `https://<DOMAIN>/api/auth/github/callback`

Client ID и Client secret положи в `app.env` (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`).

## Redis и worker

Оценщик промптов гоняет прогоны в фоне:

- `redis` (`redis:7`): очередь прогонов. Порт наружу не публикуется, секретов в нём нет. Данные лежат в анонимном томе образа: переживают `up -d` с пересозданием контейнера, но теряются при `docker compose down`: следующий `up` создаёт контейнер с новым томом (`down -v` удаляет и старый). На них ничего не опирается: если Redis потеряет очередь, `worker` при старте ставит `queued` прогоны заново, а `running` переводит в `failed`.
- `worker`: образ `api`, команда `taskiq worker app.worker:broker --workers 1 --max-async-tasks 2`: один процесс, не больше двух прогонов одновременно. Читает тот же `app.env`, что и `api`.
- Адрес Redis `REDIS_URL=redis://redis:6379/0` задан в `docker-compose.yml` для `api` и `worker` (внутренний адрес, не секрет), в `app.env` его добавлять не нужно. Если строка `REDIS_URL` там всё же есть, значение из `docker-compose.yml` приоритетнее.
- Образ `api` содержит `content/*/tasks/*.yaml` и `*.mdx` в `/app/content`: YAML со скрытыми кейсами Тренажёра читает только API. В образ `web` попадает только MDX, YAML туда не должен попасть.
- Задачи симулятора (`content/*/simulator/*.yaml` и `*.mdx`) едут так же: YAML со скрытыми целями только в `api`, в `web` одни MDX. Это проверяет `make check-images`. Симулятору не нужна новая переменная в `app.env`: AI-разбор идёт через судью оценщика (`ANTHROPIC_API_KEY`, `EVALS_LLM_BACKEND`), а лимит 20 отправок за 24 часа на пользователя задан в коде, не в настройках.

Переменные в `app.env` (значения из `infra/app.env.example`):

| Имя | Значение |
| --- | --- |
| `ANTHROPIC_API_KEY` | ключ Anthropic API, нужен при `EVALS_LLM_BACKEND=anthropic` |
| `EVALS_LLM_BACKEND` | `anthropic`; `fake` отдаёт ответы-заглушки без обращений к API. Значение `claude_cli` (вход Claude Code на машине) только для локальной работы, на сервере его не ставь |
| `EVALS_RUN_COST_LIMIT_USD` | предельная стоимость одного прогона, по умолчанию 5 |
| `EVALS_CONCURRENCY` | сколько кейсов одного прогона идут параллельно, по умолчанию 4 |
| `CODE_REVIEW_DAILY_LIMIT` | сколько проверок кода один пользователь может отправить за сутки, по умолчанию 10 |
| `CONTENT_DIR` | `/app/content`; то же значение уже задано в образе `api`, в `app.env` оно нужно только для переопределения |

На уже работающем сервере допиши эти переменные в `app.env` до первого деплоя этой версии. После правки `app.env` перезапусти оба сервиса: `docker compose up -d api worker`.

## Бэкапы

Сервис `backup` (образ `ghcr.io/hhaakkimm/devplus-backup`, исходники в `infra/backup/`) раз в сутки в 03:00 UTC запускает `crond` → `/backup.sh`: `pg_dump --clean --if-exists | gzip` и загрузка файла `devplus-<дата-время UTC>.sql.gz` в S3-совместимое хранилище. Хранилище любое с S3 API, провайдера выбираешь ты.

Переменные в `app.env` (значения из `infra/app.env.example`):

| Имя | Значение |
| --- | --- |
| `BACKUP_S3_ENDPOINT` | адрес S3 API провайдера, например `https://s3.example.com` |
| `BACKUP_S3_BUCKET` | имя бакета, он должен уже существовать |
| `BACKUP_S3_ACCESS_KEY` | ключ доступа |
| `BACKUP_S3_SECRET_KEY` | секретный ключ |

Если провайдер проверяет регион подписи, добавь в `app.env` строку `AWS_DEFAULT_REGION=<регион>`: `aws` читает её сам. Команде `put-bucket-lifecycle-configuration` ниже, которую ты запускаешь в своём shell, нужен тот же регион: `export AWS_DEFAULT_REGION=<регион>` перед ней.

Пароль к Postgres скрипт берёт из `POSTGRES_PASSWORD`. Все значения приходят в контейнер из `app.env`, `crond` передаёт их задачам. После правки `app.env` перезапусти сервис: `docker compose up -d backup`.

### Настроить хранилище (один раз)

1. Создай приватный бакет **только под бэкапы** и ключ доступа только к нему, с правом читать и писать объекты. Ключ и адрес API провайдера пропиши в `app.env` до первого деплоя этой версии: без них `backup` запустится, но в 03:00 завершится с ошибкой.
2. Задай правило жизненного цикла: удалять объекты старше 14 дней, префикс пустой. Пустой префикс значит «весь бакет», поэтому бакет обязан быть выделенным: всё, что в нём лежит, исчезнет через 14 дней. Скрипт сам ничего не удаляет, срок хранения держит бакет. В консоли провайдера это правило «expiration» на 14 дней. Через `aws` с ключом, которому разрешено менять настройки бакета:

   ```bash
   aws s3api put-bucket-lifecycle-configuration --bucket <бакет> --endpoint-url <endpoint> \
     --lifecycle-configuration '{"Rules":[{"ID":"expire-14d","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":14}}]}'
   ```

   По желанию добавь в тот же `Rules` второе правило, которое чистит оборванные multipart-загрузки: `{"ID":"abort-multipart","Status":"Enabled","Filter":{"Prefix":""},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":2}}`. Команда заменяет всю конфигурацию бакета, поэтому оба правила идут одним вызовом.

### Проверка бэкапа

На сервере, в `/opt/devplus`:

```bash
docker compose exec backup /backup.sh
```

В конце вывода `backup OK: devplus-<дата>.sql.gz`, файл лежит в бакете. После 03:00 в `docker compose logs backup` есть строки `crond: USER root ... cmd /backup.sh` и `backup OK`. Сбой выглядит так: строка `backup FAILED (exit N): nothing uploaded` в логе, код выхода не 0, в бакет ничего не попадает.

Оповещения о сбое нет: смотри `docker compose logs --since 24h backup` или список файлов в бакете.

### Восстановление

Нужен свежий дамп и пустая БД. Шаг 3 стирает текущую БД: если она ещё жива, сначала сними с неё копию (шаг 2 из «Отката»). Все команды на сервере, в `/opt/devplus`. Шаги 2, 4 и 5 запускают `backup` и `migrate` через `docker compose run`, а шаг 6 поднимает весь стек, поэтому в `.env` должен стоять тег, для которого есть образ `devplus-backup` (любой деплой после появления бэкапов). Если сервер откатывали на версию без бэкапов, верни на время восстановления свежий тег: `echo IMAGE_TAG=<sha-свежего-деплоя> > .env`.

1. Остановить приложение: `docker compose stop api web worker`.
2. Посмотреть дампы, выбрать нужный:

   ```bash
   docker compose run --rm -T backup sh -c 'AWS_ACCESS_KEY_ID=$BACKUP_S3_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$BACKUP_S3_SECRET_KEY aws s3 ls "s3://$BACKUP_S3_BUCKET/" --endpoint-url "$BACKUP_S3_ENDPOINT"'
   ```

3. Пересоздать пустую БД. На новом сервере после `docker compose up -d postgres` она уже пустая, шаг пропусти:

   ```bash
   docker compose exec -T postgres psql -U devplus -d postgres -c 'DROP DATABASE IF EXISTS devplus WITH (FORCE)' -c 'CREATE DATABASE devplus'
   ```

4. Залить дамп (`-v ON_ERROR_STOP=1` останавливает заливку на первой ошибке, `pipefail`: сбой скачивания не останется незамеченным):

   ```bash
   docker compose run --rm -T backup sh -c '
     set -eo pipefail
     export PGPASSWORD=$POSTGRES_PASSWORD AWS_ACCESS_KEY_ID=$BACKUP_S3_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$BACKUP_S3_SECRET_KEY
     aws s3 cp "s3://$BACKUP_S3_BUCKET/devplus-<дата>.sql.gz" - --endpoint-url "$BACKUP_S3_ENDPOINT" | gunzip | psql -v ON_ERROR_STOP=1 -h postgres -U devplus devplus'
   ```

5. Проверить ревизию схемы: `docker compose run --rm migrate alembic current`. `(head)` в ответе значит, что схема соответствует текущему образу. Если ревизия старее, следующий `up` накатит миграции сервисом `migrate`.
6. Запустить всё: `docker compose up -d --wait`. Строки на месте: `docker compose exec -T postgres psql -U devplus devplus -c 'SELECT count(*) FROM users'`.

### Проверка восстановления

Сделай её после настройки бэкапов и потом раз в квартал: дамп, который ни разу не разворачивали, бэкапом считать нельзя. Нужен тот же тег в `.env`, что и для восстановления (с образом `devplus-backup`). Рабочая БД не затрагивается, дамп заливается во временную `restore_check`:

```bash
docker compose exec -T postgres psql -U devplus -d postgres -c 'CREATE DATABASE restore_check'
```

Затем команда из шага 4 «Восстановления» с `restore_check` вместо `devplus` в конце, потом:

```bash
docker compose exec -T postgres psql -U devplus restore_check -c 'SELECT version_num FROM alembic_version' -c 'SELECT count(*) FROM users'
docker compose run --rm migrate alembic heads    # версия из дампа совпадает, если дамп сделан на текущей схеме
docker compose exec -T postgres psql -U devplus -d postgres -c 'DROP DATABASE restore_check'
```

### Проверить бэкап локально, без сервера

`infra/docker-compose.backup-test.yml` поднимает Postgres, MinIO и `backup` с расписанием «каждую минуту» (тот же crontab, другое время) и фальшивыми ключами. Порты наружу: только Postgres на `127.0.0.1:55432`, dev-стек не трогается.

```bash
docker compose -f infra/docker-compose.backup-test.yml up -d --build --wait
docker compose -f infra/docker-compose.backup-test.yml exec backup sh -c 'AWS_ACCESS_KEY_ID=$BACKUP_S3_ACCESS_KEY AWS_SECRET_ACCESS_KEY=$BACKUP_S3_SECRET_KEY aws s3 mb "s3://$BACKUP_S3_BUCKET" --endpoint-url "$BACKUP_S3_ENDPOINT"'
# дальше: миграции в тестовую БД (DATABASE_URL=postgresql+asyncpg://devplus:test-password@127.0.0.1:55432/devplus),
# строка в users, /backup.sh вручную и минутой позже по расписанию, восстановление как выше
docker compose -f infra/docker-compose.backup-test.yml down -v
```

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

На сервере `docker compose ps` показывает `redis` здоровым, а `worker` и `backup` запущенными. Бэкап проверяется отдельно, см. «Бэкапы».

## Откат

Старые образы остаются в GHCR под своими тегами, следующий деплой перезапишет `.env`. Все команды, кроме `git diff`, выполняй на сервере, в `/opt/devplus`. `<текущий-sha>` смотри там же: `cat /opt/devplus/.env`.

Откат на версию до оценщика промптов и бэкапов: в её образе нет `app.worker`, а образов `worker` и `backup` под её тегом нет, и `docker compose up` без списка сервисов падает на скачивании. В обоих вариантах ниже для такого тега есть отдельная команда.

Сначала проверь в клоне репозитория, менялась ли схема БД между версиями:

```bash
git diff --stat <старый-sha> <текущий-sha> -- apps/api/migrations
```

**Миграций между версиями нет.** Просто переключи тег:

```bash
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait
```

Для тега без образов `worker` и `backup` (до оценщика и бэкапов) эта команда упадёт на скачивании. Для такого тега останови `worker` (в образе старой версии нет `app.worker`) и поднимай только сервисы, у которых образ есть. Контейнер `backup` остаётся запущенным со своим образом, бэкапы идут:

```bash
docker compose stop worker
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait postgres redis migrate api web caddy
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
# 5. переключить тег (для тега без образов worker и backup: команда из блока ниже)
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait
```

Для тега без образов `worker` и `backup` (до оценщика и бэкапов) шаг 5 выглядит так (`worker` уже остановлен на шаге 1 и остаётся остановленным, `backup` остаётся запущенным со своим образом):

```bash
echo IMAGE_TAG=<старый-sha> > .env && docker compose up -d --wait postgres redis migrate api web caddy
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
