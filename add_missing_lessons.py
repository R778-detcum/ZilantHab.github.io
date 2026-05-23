import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from main.models import Course, Lesson

course = Course.objects.get(slug='tatarskii-yazyk-s-nulya')
for i in range(3, 51):
    lesson, created = Lesson.objects.get_or_create(
        course=course,
        order=i,
        defaults={
            'title': f'Урок {i}',
            'section': 'Продолжение',
            'content': f'<p>Материал урока {i}.</p>',
            'duration_minutes': 15,
            'is_free_preview': True,
        }
    )
    if created:
        print(f'✅ Добавлен урок {i}')

print('Готово! Теперь в курсе 50 уроков.')