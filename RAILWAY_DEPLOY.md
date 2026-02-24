# Деплой Digital Neighbour Bot на Railway

## Подготовка

### 1. Файлы конфигурации

Проект уже содержит все необходимые файлы для деплоя на Railway:

- ✅ [`Procfile`](Procfile) - команда запуска бота
- ✅ [`runtime.txt`](runtime.txt) - версия Python
- ✅ [`requirements.txt`](requirements.txt) - зависимости проекта
- ✅ [`railway.json`](railway.json) - конфигурация Railway
- ✅ [`.railwayignore`](.railwayignore) - исключаемые файлы

### 2. Переменные окружения

Перед деплоем убедитесь, что у вас есть токен Telegram бота.

## Шаги деплоя

### Вариант 1: Через веб-интерфейс Railway

1. **Создайте аккаунт на Railway**
   - Перейдите на https://railway.app
   - Войдите через GitHub

2. **Создайте новый проект**
   - Нажмите "New Project"
   - Выберите "Deploy from GitHub repo"
   - Выберите репозиторий `digital_neigbour_bot`

3. **Настройте переменные окружения**
   - Перейдите в раздел "Variables"
   - Добавьте переменную:
     ```
     BOT_TOKEN=ваш_токен_бота
     ```

4. **Деплой**
   - Railway автоматически обнаружит `Procfile` и начнет деплой
   - Дождитесь завершения сборки (обычно 2-3 минуты)

5. **Проверка**
   - Перейдите в раздел "Deployments"
   - Проверьте логи на наличие ошибок
   - Отправьте `/start` вашему боту в Telegram

### Вариант 2: Через Railway CLI

1. **Установите Railway CLI**
   ```bash
   npm i -g @railway/cli
   ```

2. **Войдите в аккаунт**
   ```bash
   railway login
   ```

3. **Инициализируйте проект**
   ```bash
   cd digital_neighbour_bot
   railway init
   ```

4. **Добавьте переменные окружения**
   ```bash
   railway variables set BOT_TOKEN=ваш_токен_бота
   ```

5. **Деплой**
   ```bash
   railway up
   ```

6. **Просмотр логов**
   ```bash
   railway logs
   ```

## Конфигурация Railway

### Procfile
```
worker: python bot.py
```
Указывает Railway запустить бота как worker процесс (не веб-сервер).

### railway.json
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Настройки:
- **builder**: NIXPACKS - автоматическое определение окружения
- **numReplicas**: 1 - один экземпляр бота
- **restartPolicyType**: ON_FAILURE - перезапуск при ошибке
- **restartPolicyMaxRetries**: 10 - максимум 10 попыток перезапуска

## База данных

### SQLite (текущая конфигурация)

По умолчанию бот использует SQLite (`reminders.db`). На Railway:

⚠️ **Важно**: Railway использует эфемерное хранилище. При перезапуске контейнера база данных будет потеряна.

**Решения:**

1. **Railway Volume (рекомендуется)**
   - В настройках проекта добавьте Volume
   - Примонтируйте к `/app/data`
   - Обновите `config/settings.py`:
     ```python
     DB_PATH = Path("/app/data/reminders.db")
     ```

2. **PostgreSQL (для продакшена)**
   - Добавьте PostgreSQL сервис в Railway
   - Обновите код для работы с PostgreSQL
   - Добавьте `psycopg2-binary` в `requirements.txt`

### Миграция на PostgreSQL (опционально)

Если нужна надежная БД:

1. **Добавьте PostgreSQL в Railway**
   - В проекте нажмите "New" → "Database" → "PostgreSQL"
   - Railway автоматически создаст переменную `DATABASE_URL`

2. **Обновите зависимости**
   ```txt
   # requirements.txt
   psycopg2-binary==2.9.9
   sqlalchemy==2.0.23
   ```

3. **Обновите код**
   - Замените SQLite на PostgreSQL в `database/store.py`
   - Используйте `DATABASE_URL` из переменных окружения

## Мониторинг

### Логи
```bash
railway logs
```

### Метрики
- Перейдите в раздел "Metrics" в веб-интерфейсе
- Отслеживайте использование CPU, памяти, сети

### Алерты
- Настройте уведомления в разделе "Settings" → "Notifications"
- Получайте уведомления о сбоях на email

## Обновление бота

### Автоматическое обновление
Railway автоматически деплоит при push в main ветку:

```bash
git add .
git commit -m "update: описание изменений"
git push origin main
```

### Ручное обновление
```bash
railway up
```

## Переменные окружения

### Обязательные
- `BOT_TOKEN` - токен Telegram бота

### Опциональные
- `DATABASE_URL` - URL PostgreSQL (если используется)
- `LOG_LEVEL` - уровень логирования (DEBUG, INFO, WARNING, ERROR)

## Troubleshooting

### Бот не отвечает
1. Проверьте логи: `railway logs`
2. Убедитесь, что `BOT_TOKEN` установлен правильно
3. Проверьте статус деплоя в веб-интерфейсе

### База данных пустая после перезапуска
1. Настройте Railway Volume (см. раздел "База данных")
2. Или мигрируйте на PostgreSQL

### Ошибки при деплое
1. Проверьте `requirements.txt` на корректность версий
2. Убедитесь, что `runtime.txt` содержит поддерживаемую версию Python
3. Проверьте логи сборки в Railway

### Бот падает с ошибкой
1. Проверьте логи: `railway logs --tail 100`
2. Убедитесь, что все зависимости установлены
3. Проверьте код на наличие ошибок

## Стоимость

Railway предоставляет:
- **Hobby Plan**: $5/месяц или 500 часов бесплатно
- **Developer Plan**: $20/месяц

Для этого бота достаточно Hobby Plan.

## Полезные команды

```bash
# Просмотр статуса
railway status

# Просмотр переменных
railway variables

# Открыть проект в браузере
railway open

# Перезапуск
railway restart

# Удаление проекта
railway delete
```

## Дополнительные ресурсы

- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [Aiogram Documentation](https://docs.aiogram.dev)

## Поддержка

При возникновении проблем:
1. Проверьте логи Railway
2. Изучите документацию Railway
3. Создайте issue в репозитории проекта
