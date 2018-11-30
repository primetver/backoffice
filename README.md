# backoffice
Простой сервис планирования и учета ресурсов рабочих групп проектов

Для запуска: 

1. Установите необходимые пакеты в текущее окружение `pip install -r requirements.txt` 
2. Скопируйте  `.env-template` в `.env`.
3. При необходимости, отредактируйте параметр `DATABASE_URL` в  `.env` для доступа к требуемой базе данных. 
Данный шаг не обязателен, по умолчанию используется sqlite3. 
4. `python manage.py migrate`
5. `python manage.py createsuperuser`
6. `python manage.py runserver`

Приложение доступно: `http://localost:8000`
