# backoffice
Простой сервис планирования и учета ресурсов рабочих групп проектов


Для запуска: 

1. Скопируйте  `.env-template` в `.env`.
2. При необходимости, отредактируйте параметр `DATABASE_URL` в  `.env` для доступа к требуемой базе данных. 
Данный шаг не обязателен, по умолчанию используется sqlite3. 
3. `python manage.py migrate`
4. `python manage.py createsuperuser`
5. `python manage.py runserver`

Приложение доступно: `http://localost:8000`
