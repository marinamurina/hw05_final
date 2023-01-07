# yatube_project
Социальная сеть блогеров.

### Описание.
Социальная сеть с возможностью создавать посты, группы, оставлять комментарии, подписываться на понравившихся авторов и группы.

Что могут делать пользователи:

Залогиненные пользователи могут:
Просматривать, публиковать, удалять и редактировать свои публикации;
Просматривать информацию о сообществах;
Просматривать и публиковать комментарии от своего имени к публикациям других пользователей, удалять и редактировать свои комментарии;
Подписываться на других пользователей и просматривать свои подписки.
Примечание: Доступ ко всем операциям записи, обновления и удаления доступны только после аутентификации и получения токена.

Анонимные пользователи могут:
Просматривать публикации;
Просматривать информацию о сообществах;
Просматривать комментарии.

### Технологии
Python 3.7, Django 2.2, Pytest 6.2, Pillow 8.3, Requests 2.26, Thumbnail 12.7

### Запуск проекта в dev-режиме
- Установите и активируйте виртуальное окружение
- Установите зависимости из файла requirements.txt
```
pip install -r requirements.txt
``` 
- В папке с файлом manage.py выполните миграции:
```
python3 manage.py migrate
```
- В папке с файлом manage.py выполните команду:
```
python3 manage.py runserver
```
### Автор
Мурина Марина.
