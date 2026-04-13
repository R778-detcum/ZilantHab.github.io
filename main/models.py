from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Course(models.Model):
    """Модель для курсов"""
    LEVEL_CHOICES = [
        ('beginner', 'Начинающий'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
        ('archived', 'В архиве'),
    ]

    # Основная информация
    title = models.CharField('Название курса', max_length=200)
    slug = models.SlugField('URL-идентификатор', max_length=200, unique=True, blank=True)
    description = models.TextField('Описание курса')
    short_description = models.CharField('Краткое описание', max_length=300, blank=True)

    # Детали курса
    level = models.CharField('Уровень', max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration_weeks = models.PositiveIntegerField('Длительность (недель)', default=4)
    lessons_count = models.PositiveIntegerField('Количество уроков', default=10)

    # Цена и акции
    price = models.DecimalField('Цена (₽)', max_digits=10, decimal_places=2, default=0)
    old_price = models.DecimalField('Старая цена (₽)', max_digits=10, decimal_places=2, blank=True, null=True)
    is_free = models.BooleanField('Бесплатный', default=False)

    # Визуальное оформление
    icon_class = models.CharField('Иконка (Font Awesome)', max_length=50, default='fas fa-language')
    badge_text = models.CharField('Текст бейджа', max_length=50, blank=True, help_text='Например: "🔥 АКЦИЯ"')
    badge_color = models.CharField('Цвет бейджа', max_length=20, default='warning')

    # Статус и даты
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    published_at = models.DateTimeField('Опубликован', blank=True, null=True)

    # Порядок отображения
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def display_price(self):
        """Отображаемая цена"""
        if self.is_free:
            return 'Бесплатно'
        return f'{self.price} ₽'

    @property
    def has_sale(self):
        """Есть ли скидка"""
        return self.old_price and self.old_price > self.price


class Lesson(models.Model):
    """Модель для уроков"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='Курс')
    title = models.CharField('Название урока', max_length=200)
    order = models.PositiveIntegerField('Порядок', default=0)
    section = models.CharField('Раздел', max_length=100, blank=True, help_text='Например: Основы, Повседневная речь')

    # Контент урока
    video_url = models.URLField('Ссылка на видео', blank=True)
    content = models.TextField('Содержание урока', blank=True, help_text='HTML формат')
    duration_minutes = models.PositiveIntegerField('Длительность (минут)', default=10)

    # Дополнительно
    is_free_preview = models.BooleanField('Бесплатный просмотр', default=False)

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['course', 'order']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class Community(models.Model):
    """Модель для сообществ"""
    name = models.CharField('Название сообщества', max_length=100)
    icon_class = models.CharField('Иконка (Font Awesome)', max_length=50, default='fas fa-users')
    description = models.CharField('Краткое описание', max_length=200)
    member_count = models.PositiveIntegerField('Количество участников', default=0)
    is_active = models.BooleanField('Активно', default=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Сообщество'
        verbose_name_plural = 'Сообщества'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Achievement(models.Model):
    """Модель для достижений"""
    name = models.CharField('Название достижения', max_length=100)
    icon_class = models.CharField('Иконка (Font Awesome)', max_length=50, default='fas fa-medal')
    description = models.CharField('Описание', max_length=200)
    points = models.PositiveIntegerField('Очки', default=10)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Достижение'
        verbose_name_plural = 'Достижения'

    def __str__(self):
        return self.name


class Profile(models.Model):
    """Модель профиля пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField('О себе', max_length=500, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    city = models.CharField('Город', max_length=100, blank=True)

    total_points = models.PositiveIntegerField('Всего очков', default=0)
    coins = models.PositiveIntegerField('Монеты', default=0)
    lessons_completed = models.PositiveIntegerField('Пройдено уроков', default=0)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    last_active = models.DateTimeField('Последняя активность', auto_now=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'


# Сигналы для автоматического создания профиля
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Question(models.Model):
    """Вопрос для теста к уроку"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions', verbose_name='Урок')
    text = models.TextField('Текст вопроса')
    option1 = models.CharField('Вариант 1', max_length=200)
    option2 = models.CharField('Вариант 2', max_length=200)
    option3 = models.CharField('Вариант 3', max_length=200, blank=True)
    option4 = models.CharField('Вариант 4', max_length=200, blank=True)
    correct_option = models.PositiveSmallIntegerField('Номер правильного ответа (1-4)', choices=[(i, str(i)) for i in range(1, 5)])
    explanation = models.TextField('Пояснение к ответу', blank=True)

    class Meta:
        verbose_name = 'Вопрос теста'
        verbose_name_plural = 'Вопросы тестов'
        ordering = ['id']

    def __str__(self):
        return f'{self.lesson.title} - {self.text[:50]}'


class LessonCompletion(models.Model):
    """Отметка о прохождении урока пользователем"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_lessons')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    test_score = models.PositiveSmallIntegerField('Результат теста (%)', default=0)

    class Meta:
        verbose_name = 'Пройденный урок'
        verbose_name_plural = 'Пройденные уроки'
        unique_together = ['user', 'lesson']  # один урок нельзя пройти дважды

    def __str__(self):
        return f'{self.user.username} - {self.lesson.title}'