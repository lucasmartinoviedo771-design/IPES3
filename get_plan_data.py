import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'academia_project.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute('SELECT * FROM academia_horarios_plan')
    rows = cursor.fetchall()
    for row in rows:
        print(row)
