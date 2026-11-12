# devplus: Квизы и контент из Hello Interview. План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Команде доступны 50 квизов на русском (после урока и в общем каталоге) с сохранением результатов, а 184 статьи Hello Interview переведены и лежат уроками на сайте.

**Architecture:** Новый модуль бэкенда `quiz` хранит только результаты (`quiz_results`). Сами квизы это JSON-файлы в `content/<NN>/quizzes/`, web читает их с диска и проверяет ответы в браузере. Статьи конвертируются одноразовым скриптом в `content/2x-*/NN-slug.mdx` и подхватываются существующим загрузчиком уроков.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, dishka (всё уже есть); Next.js App Router, Tailwind, vitest, Playwright. Новых зависимостей нет.

**Spec:** `docs/superpowers/specs/2026-11-12-devplus-quizzes-design.md` (утверждена 2026-11-12)

## Global Constraints

- Модуль `quiz`, путь `apps/api/app/modules/quiz/`, API под `/api/quizzes/*`. Импортирует только `app.modules.auth.service`; контракты import-linter в `apps/api/pyproject.toml` по образцу `progress`, плюс обратные («остальные не зависят от quiz»).
- Slug квиза `<module>/<quiz>` по шаблону `^[a-z0-9-]+$`, общая длина ≤200.
- Результат: `0 ≤ score ≤ total`, `1 ≤ total ≤ 200`, иначе 422.
- Миграции только через Alembic, сгенерированную читать глазами. После изменения API `make gen-client` и коммит клиента.
- Квиз-файл: формат из раздела 2 спецификации; загрузчик падает с именем файла на любом нарушении.
- Секретов и новых переменных окружения нет.
- Ответ пользователю по-русски, термины английские.

## Структура файлов

- Создать: `apps/api/app/modules/quiz/{__init__,models,schemas,service,router,providers}.py`, миграция `quiz_results`, `apps/api/tests/test_quiz.py`
- Изменить: `apps/api/app/factory.py` (роутер), контейнер dishka (провайдер), `apps/api/pyproject.toml` (контракты), `packages/api-client` (генерация)
- Создать (web): `apps/web/lib/quizzes.ts`, `apps/web/lib/quiz-state.ts`, `apps/web/components/quiz.tsx`, `apps/web/components/quiz-link.tsx`, `apps/web/app/(app)/quizzes/page.tsx`, `apps/web/app/(app)/quizzes/[module]/[quiz]/page.tsx`, `apps/web/test/quizzes.test.ts`, `apps/web/test/quiz-state.test.ts`, `apps/web/e2e/quizzes.spec.ts`
- Изменить (web): `apps/web/components/header.tsx`, `apps/web/app/(app)/lessons/[module]/[lesson]/page.tsx`, `apps/web/lib/content.ts` (поле `quiz` в `LessonMeta`)
- Контент: `content/2x-*/`, `content/*/quizzes/*.json`, `apps/web/public/content/`

## Tasks

### Task 1. Бэкенд: модель, миграция, сервис, API

- [x] Тест `test_quiz.py` (по образцу `test_progress.py`): пустой список; первая отправка создаёт результат; худший результат не затирает лучший, `attempts` растёт; лучший заменяется; `total` последней попытки перезаписывается; `score>total`, `score<0`, `total=0`, `total>200` дают 422; плохой slug 422; без входа 401; результаты разных пользователей не пересекаются.
- [x] `models.py` (`QuizResult`), миграция `alembic revision --autogenerate`, прочитать глазами, `make migrate`, `make migrate-check`.
- [x] `service.py` (`record`: один `INSERT … ON CONFLICT DO UPDATE` с `CASE` по доле, `list_results`), `schemas.py`, `router.py`, `providers.py`, подключить роутер и провайдер.
- [x] Контракты import-linter, `make lint` (api часть) и `pytest apps/api/tests/test_quiz.py`.
- [x] `make gen-client`, коммит.

### Task 2. Web: формат, загрузчик, логика квиза

- [ ] Тест `quizzes.test.ts` на фикстурах: корректный квиз читается; падение с именем файла для: неверного типа, `choice` не с 4 вариантами, `answer` вне диапазона, `ranking`/`matching`, где `answer` не перестановка, `matching` с разной длиной `left`/`right`, неизвестного `level`, пустого `question`/`explanation`; каталог сгруппирован по модулям; slug из URL не попадает в путь.
- [ ] `lib/quizzes.ts`: `loadQuizCatalog()`, `loadQuiz(module, slug)`.
- [ ] Тест `quiz-state.test.ts`: `isCorrect` для 4 типов, `score`, `wrongIndexes`.
- [ ] `lib/quiz-state.ts`.

### Task 3. Web: страницы и компонент

- [ ] `components/quiz.tsx` (клиентский): один вопрос за раз, 4 типа, объяснение после ответа, экран результата, «Повторить ошибки», «Пройти заново», `PUT` результата при завершении полного прохождения (повтор ошибок результат не отправляет).
- [ ] `/quizzes` (каталог) и `/quizzes/[module]/[quiz]`, пункт «Квизы» в шапке.
- [ ] `loadQuizResults()` в `lib/session.ts` (по образцу `loadDone`).
- [ ] Поле `quiz` во frontmatter урока, блок `quiz-link.tsx` под уроком.
- [ ] e2e `quizzes.spec.ts`: пройти квиз-фикстуру, увидеть результат, перезагрузить каталог и увидеть лучший результат.

### Task 4. Конвертер квизов и перевод

- [ ] Скрипт (в scratchpad, не в репозиторий): `json` выгрузки → формат раздела 2, slug и модуль квиза по таблице, `source`-ссылка.
- [ ] Скрипт перевода через `claude -p` с параллелизмом: переводит `title`, `question`, `options`, `items`, `left`, `right`, `explanation`; числовые поля и порядок не трогает; проверка: структура и `answer` идентичны оригиналу, иначе повтор.
- [ ] Положить 50 квизов в `content/*/quizzes/`, прогнать загрузчик и тесты.

### Task 5. Конвертер статей и перевод

- [ ] Скрипт: md → mdx (чистка, экранирование, ссылки, картинки), модули и `_module.json`, frontmatter `title`, `summary`, `quiz`.
- [ ] Скрипт перевода через `claude -p`: чанки по заголовкам для длинных статей, проверка числа блоков кода/картинок/заголовков.
- [ ] Скопировать используемые картинки в `apps/web/public/content/`.
- [ ] `content-compile` проходит; ручная выборка нескольких статей в браузере.

### Task 6. Завершение

- [ ] `make lint`, `make test`, `make e2e` (если окружение позволяет), `make check-images`.
- [ ] Обновить `docs/roadmap.html`, шапку спеки/плана, закоммитить, перепубликовать артефакт.
- [ ] `CLAUDE.md`: короткая строка про модуль `quiz` и папки `quizzes/`.
