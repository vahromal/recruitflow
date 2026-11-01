# Развёртывание RecruitFlow на VPS

Пошаговая инструкция для новичка: от покупки сервера до рабочего HTTPS-сайта с бэкапами.
Все команды выполняются по порядку. Замените `example.com` на свой домен, а `SERVER_IP` — на
IP сервера.

Что понадобится:

- VPS с Ubuntu 24.04 LTS, минимум 2 vCPU / 4 ГБ RAM / 40 ГБ диска;
- домен;
- SSH-доступ к серверу.

## 1. Купить VPS

Подойдёт любой провайдер. Примеры:

- **Hetzner** — недорогие серверы в Германии/Финляндии (CX22 и подобные);
- **DigitalOcean** — Droplet с Ubuntu 24.04;
- **TimeWeb** — российский провайдер, если нужен российский биллинг.

При создании выберите **Ubuntu 24.04 LTS** и добавьте свой SSH-ключ, если провайдер это
предлагает. Для GDPR рекомендуется брать сервер в ЕС (Германия, Финляндия, Нидерланды):
персональные данные кандидатов будут храниться в ЕС.

Запишите публичный IP сервера — он понадобится дальше.

## 2. Купить домен и настроить DNS

Купите домен у любого регистратора. В панели управления DNS добавьте запись:

| Тип | Имя | Значение |
|---|---|---|
| A | `@` (или `example.com`) | `SERVER_IP` |

Если нужен `www`, добавьте ещё одну A-запись для `www` на тот же IP. Изменения DNS могут
применяться от нескольких минут до нескольких часов. Проверка с локального компьютера:

```bash
dig +short example.com
```

Команда должна вернуть IP вашего сервера. Без этого HTTPS-сертификат не выпустится.

## 3. Подключиться по SSH и создать пользователя

Подключитесь к серверу как root:

```bash
ssh root@SERVER_IP
```

Создайте отдельного пользователя (дальше работаем под ним, а не под root):

```bash
adduser deploy
usermod -aG sudo deploy
```

Скопируйте SSH-ключ root новому пользователю, чтобы не потерять доступ:

```bash
rsync --archive --chown=deploy:deploy /root/.ssh /home/deploy/
```

Если каталога `/root/.ssh` нет (сервер создавался с входом по паролю), пропустите эту
команду — ключ скопируем ниже.

Если SSH-ключа ещё нет, создайте его **на своём компьютере** (не на сервере):

```bash
ssh-keygen -t ed25519 -C "you@example.com"
ssh-copy-id deploy@SERVER_IP
```

Проверьте вход и переключитесь на нового пользователя:

```bash
ssh deploy@SERVER_IP
```

Опционально (делайте только если вход по ключу уже проверен) можно отключить вход root и
пароли в `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
```

Затем `sudo systemctl restart ssh`. Если что-то пойдёт не так, доступ по ключу для `deploy`
должен остаться рабочим.

## 4. Настроить firewall

Разрешаем только SSH, HTTP и HTTPS. Порт PostgreSQL (5432) наружу не открываем — в
`docker-compose.prod.yml` он вообще не публикуется, база доступна только внутри Docker-сети.

```bash
sudo apt update
sudo apt install -y ufw
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp
sudo ufw enable
sudo ufw status verbose
```

На вопрос про включение firewall ответьте `y`. В статусе должны быть разрешены `22`, `80`,
`443`, а `5432` — запрещён.

## 5. Установить Docker и Docker Compose

Официальная инструкция Docker для Ubuntu (подходит для 24.04):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Разрешите пользователю `deploy` работать с Docker без sudo:

```bash
sudo usermod -aG docker $USER
```

**Важно:** изменения группы применяются после повторного входа. Выйдите и зайдите снова:

```bash
exit
ssh deploy@SERVER_IP
docker compose version
```

`docker compose version` должен показать версию v2 (например, `v2.x.x`).

## 6. Клонировать проект и заполнить .env

```bash
sudo mkdir -p /opt/RecruitFlow
sudo chown $USER:$USER /opt/RecruitFlow
git clone <URL-репозитория> /opt/RecruitFlow
cd /opt/RecruitFlow
cp .env.example .env
```

Сгенерируйте секреты:

```bash
openssl rand -hex 32   # для SECRET_KEY
openssl rand -hex 24   # для POSTGRES_PASSWORD
```

Откройте `.env` и заполните значения (без пробелов вокруг `=`):

```bash
nano .env
```

```dotenv
POSTGRES_USER=recruitflow
POSTGRES_PASSWORD=<вставьте результат openssl rand -hex 24>
POSTGRES_DB=recruitflow

SECRET_KEY=<вставьте результат openssl rand -hex 32>

CORS_ORIGINS=https://example.com,https://www.example.com

DOMAIN=example.com
EMAIL=admin@example.com

MAX_UPLOAD_SIZE_MB=10
```

Закройте файл (в nano: `Ctrl+O`, `Enter`, `Ctrl+X`) и ограничьте доступ:

```bash
chmod 600 .env
```

`DOMAIN` — домен без `https://` и без слэша. `EMAIL` — ваша почта для уведомлений Let's Encrypt.
`CORS_ORIGINS` должен содержать именно те адреса, с которых открывается сайт.

## 7. Первый деплой

```bash
cd /opt/RecruitFlow
docker compose -f docker-compose.prod.yml up -d --build
```

Первый запуск занимает несколько минут: собираются образы, запускается PostgreSQL, backend
применяет миграции Alembic, Caddy получает сертификат Let's Encrypt.

Проверьте контейнеры и health-check:

```bash
docker compose -f docker-compose.prod.yml ps
curl -fsS https://example.com/health
```

Ожидаемый ответ:

```json
{"status":"ok","service":"RecruitFlow","env":"prod"}
```

Если `curl` не отвечает:

- убедитесь, что DNS уже указывает на сервер (`dig +short example.com`);
- проверьте, что открыты порты 80 и 443 (`sudo ufw status`);
- посмотрите логи: `docker compose -f docker-compose.prod.yml logs -f caddy`.

### Примечание про DOMAIN и EMAIL для Caddy

Caddy читает `DOMAIN` и `EMAIL` из переменных окружения **своего контейнера**. В текущем
`docker-compose.prod.yml` сервис `caddy` не получает их автоматически (`.env` используется
только для подстановки в compose-файл). Если контейнер `caddy` падает с ошибкой разбора
Caddyfile, добавьте в сервис `caddy`:

```yaml
    environment:
      DOMAIN: ${DOMAIN}
      EMAIL: ${EMAIL}
```

После правки выполните:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f caddy
```

Альтернатива — вписать домен и email прямо в `deploy/Caddyfile` вместо `{$DOMAIN}` и
`{$EMAIL}`.

## 8. Миграции и создание администратора

Миграции применяются автоматически при каждом старте backend-контейнера — команда запуска
описана в `backend/Dockerfile`: `alembic upgrade head && uvicorn ...`. Отдельно ничего
запускать не нужно. Проверить можно по логам:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep -i alembic
```

Скрипт `app.seed` создаёт демо-данные и **только для разработки**: при `ENVIRONMENT=prod` он
отказывается работать. Для продакшена создайте первого администратора вручную — выполните
команду в контейнере backend:

```bash
cd /opt/RecruitFlow
docker compose -f docker-compose.prod.yml exec -T backend python -c '
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole

email = "admin@example.com"
password = "ChangeMe123!"

db = SessionLocal()
if db.query(User).filter(User.email == email).first():
    print("Пользователь уже существует:", email)
else:
    db.add(User(
        email=email,
        full_name="Администратор",
        hashed_password=hash_password(password),
        role=UserRole.ADMIN,
    ))
    db.commit()
    print("Администратор создан:", email)
db.close()
'
```

Перед запуском замените `admin@example.com` и `ChangeMe123!` на свои значения. Пароль должен
быть не короче 8 символов и надёжным. После создания войдите с этими данными (логин —
`POST /api/auth/login` или форма в интерфейсе, когда он будет готов). Остальных пользователей
админ создаёт через `POST /api/users`.

## 9. Ежедневные бэкапы

Скрипт `deploy/backup.sh` делает дамп базы (`pg_dump` + gzip), архив тома с резюме и manifest,
складывает всё в `/opt/RecruitFlow/backups` и удаляет файлы старше 14 дней.

Проверьте запуск вручную (стек должен быть запущен):

```bash
cd /opt/RecruitFlow
./deploy/backup.sh
ls -lh backups
```

В каталоге появятся файлы вида:

```
db_20261101_030000.sql.gz
resumes_20261101_030000.tar.gz
manifest_20261101_030000.txt
```

Добавьте ежедневный запуск в cron (от пользователя `deploy`):

```bash
crontab -e
```

Строка (каждый день в 03:00, лог — в домашнем каталоге):

```cron
0 3 * * * cd /opt/RecruitFlow && ./deploy/backup.sh >> /home/deploy/recruitflow-backup.log 2>&1
```

Проверьте, что задание добавлено: `crontab -l`. На следующий день посмотрите лог:

```bash
tail -n 50 /home/deploy/recruitflow-backup.log
```

Бэкапы лежат на том же сервере, поэтому дополнительно копируйте каталог `backups` в другое
место (внешний диск, S3, другой сервер) — например, через `rsync` или `rclone` по cron.
Периодически проверяйте восстановление (см. шаг 11).

## 10. Обновление приложения

Перед обновлением сделайте бэкап:

```bash
cd /opt/RecruitFlow
./deploy/backup.sh
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl -fsS https://example.com/health
```

Данные не теряются: база и резюме лежат в именованных томах (`pgdata`, `uploads`), которые
пересоздание контейнеров не затрагивает. Новые миграции Alembic применяются автоматически при
старте backend.

Если после обновления что-то сломалось, посмотрите логи (`logs -f backend`) и при
необходимости откатитесь на предыдущий коммит (`git checkout <коммит>`) и повторите
`up -d --build`.

## 11. Восстановление из бэкапа

**Внимание:** восстановление перезаписывает текущую базу. Скрипт сам делает страховочный дамп
текущего состояния в `backups/pre_restore_<дата>.sql.gz`, но лучше остановить backend, чтобы
никто не писал в базу во время восстановления.

```bash
cd /opt/RecruitFlow
docker compose -f docker-compose.prod.yml stop backend
ls -lh backups
```

Восстановить только базу:

```bash
./deploy/restore.sh backups/db_20261101_030000.sql.gz
```

Восстановить базу и резюме:

```bash
./deploy/restore.sh backups/db_20261101_030000.sql.gz --resumes backups/resumes_20261101_030000.tar.gz
```

Скрипт пересоздаёт схему `public`, заливает дамп, восстанавливает файлы резюме в том
`recruitflow_uploads` и в конце печатает количество строк в `users`, `candidates`,
`vacancies` — сверьте его с ожидаемым.

Запустите приложение обратно и проверьте:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
curl -fsS https://example.com/health
```

## 12. Проверка здоровья и диагностика

```bash
cd /opt/RecruitFlow

# статус контейнеров (должны быть running/healthy)
docker compose -f docker-compose.prod.yml ps

# health-check приложения
curl -fsS https://example.com/health

# логи backend в реальном времени
docker compose -f docker-compose.prod.yml logs -f backend

# логи Caddy (сертификаты, проксирование)
docker compose -f docker-compose.prod.yml logs -f caddy

# проверка базы изнутри контейнера
docker compose -f docker-compose.prod.yml exec db pg_isready -U recruitflow -d recruitflow
```

Типичные проблемы:

| Симптом | Что проверить |
|---|---|
| `502 Bad Gateway` | backend не запустился: `logs backend`, healthcheck, миграции |
| Нет сертификата HTTPS | DNS-запись, порты 80/443, `logs caddy` |
| Caddy не стартует | переданы ли `DOMAIN`/`EMAIL` в контейнер (см. примечание в шаге 7) |
| Не пускает по SSH после настройки firewall | `sudo ufw allow 22/tcp` (через консоль провайдера) |
| Бэкап не создаётся | запущен ли стек, права на `backups`, лог cron |
