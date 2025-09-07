import os

import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "academia_project.settings")
django.setup()

with connection.cursor() as cursor:
    try:
        cursor.execute("SELECT 1 FROM academia_horarios_horarioclase LIMIT 1;")
        print("Table academia_horarios_horarioclase exists.")
    except Exception as e:
        print(f"Table academia_horarios_horarioclase does NOT exist or is inaccessible: {e}")
