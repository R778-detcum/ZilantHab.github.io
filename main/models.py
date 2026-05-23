from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta

# ---------- Существующие модели (без изменений) ----------

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

    title = models.CharField('Название курса', max_length=200)
    slug = models.SlugField('URL-идентификатор', max_length=200, unique=True, blank=True)
    description = models.TextField('Описание курса')
    short_description = models.CharField('Краткое описание', max_length=300, blank=True)
    level = models.CharField('Уровень', max_length=20, choices=LEVEL_CHOICES, default='beginner')
    duration_weeks = models.PositiveIntegerField('Длительность (недель)', default=4)
    lessons_count = models.PositiveIntegerField('Количество уроков', default=10)
    price = models.DecimalField('Цена (₽)', max_digits=10, decimal_places=2, default=0)
    old_price = models.DecimalField('Старая цена (₽)', max_digits=10, decimal_places=2, blank=True, null=True)
    is_free = models.BooleanField('Бесплатный', default=False)
    icon_class = models.CharField('Иконка (Font Awesome)', max_length=50, default='fas fa-language')
    badge_text = models.CharField('Текст бейджа', max_length=50, blank=True, help_text='Например: "🔥 АКЦИЯ"')
    badge_color = models.CharField('Цвет бейджа', max_length=20, default='warning')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    published_at = models.DateTimeField('Опубликован', blank=True, null=True)
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
        if self.is_free:
            return 'Бесплатно'
        return f'{self.price} ₽'

    @property
    def has_sale(self):
        return self.old_price and self.old_price > self.price


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', verbose_name='Курс')
    title = models.CharField('Название урока', max_length=200)
    order = models.PositiveIntegerField('Порядок', default=0)
    section = models.CharField('Раздел', max_length=100, blank=True, help_text='Например: Основы, Повседневная речь')
    video_url = models.URLField('Ссылка на видео', blank=True)
    content = models.TextField('Содержание урока', blank=True, help_text='HTML формат')
    duration_minutes = models.PositiveIntegerField('Длительность (минут)', default=10)
    is_free_preview = models.BooleanField('Бесплатный просмотр', default=False)

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['course', 'order']

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class Community(models.Model):
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


class Question(models.Model):
    QUESTION_TYPES = [
        ('choice', 'Выбор правильного варианта'),
        ('translate', 'Перевод слова/фразы'),
        ('audio_choice', 'Прослушать и выбрать перевод'),
        ('match', 'Сопоставление'),
    ]

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions', verbose_name='Урок')
    text = models.TextField('Текст вопроса')
    option1 = models.CharField('Вариант 1', max_length=200)
    option2 = models.CharField('Вариант 2', max_length=200)
    option3 = models.CharField('Вариант 3', max_length=200, blank=True)
    option4 = models.CharField('Вариант 4', max_length=200, blank=True)
    correct_option = models.PositiveSmallIntegerField('Номер правильного ответа (1-4)', choices=[(i, str(i)) for i in range(1, 5)])
    explanation = models.TextField('Пояснение к ответу', blank=True)
    # Новые поля для Duolingo-подобных тестов
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='choice', verbose_name='Тип вопроса')
    audio_url = models.URLField('Ссылка на аудиофайл', blank=True, help_text='Для типа "audio_choice"')

    class Meta:
        verbose_name = 'Вопрос теста'
        verbose_name_plural = 'Вопросы тестов'
        ordering = ['id']

    def __str__(self):
        return f'{self.lesson.title} - {self.text[:50]}'

    def get_options(self):
        """Возвращает список (номер, текст варианта) для удобного вывода в шаблоне"""
        options = [(1, self.option1), (2, self.option2)]
        if self.option3:
            options.append((3, self.option3))
        if self.option4:
            options.append((4, self.option4))
        return options


class LessonCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_lessons')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)
    test_score = models.PositiveSmallIntegerField('Результат теста (%)', default=0)

    class Meta:
        verbose_name = 'Пройденный урок'
        verbose_name_plural = 'Пройденные уроки'
        unique_together = ['user', 'lesson']

    def __str__(self):
        return f'{self.user.username} - {self.lesson.title}'


# ---------- НОВЫЕ МОДЕЛИ (расширение профиля, лиги, экономика) ----------

# Таблица границ уровней XP
LEVEL_XP_BOUNDS = {
    1: (0, 59),
    2: (60, 119),
    3: (120, 199),
    4: (200, 299),
    5: (300, 449),
    6: (450, 749),
    7: (750, 1124),
    8: (1125, 1649),
    9: (1650, 2249),
    10: (2250, 2999),
    11: (3000, 3899),
    12: (3900, 4899),
    13: (4900, 5999),
    14: (6000, 7499),
    15: (7500, 8999),
    16: (9000, 10499),
    17: (10500, 11999),
    18: (12000, 13499),
    19: (13500, 14999),
    20: (15000, 16999),
    21: (17000, 18999),
    22: (19000, 22499),
    23: (22500, 25999),
    24: (26000, 29999),
}

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField('О себе', max_length=500, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    city = models.CharField('Город', max_length=100, blank=True)
    total_points = models.PositiveIntegerField('Всего очков (XP)', default=0)
    coins = models.PositiveIntegerField('Монеты', default=0)
    tulips = models.PositiveIntegerField('Тюльпаны (премиум валюта)', default=0)
    lessons_completed = models.PositiveIntegerField('Пройдено уроков', default=0)
    level = models.PositiveIntegerField('Уровень', default=1)
    streak_days = models.PositiveIntegerField('Дней подряд', default=0)
    last_activity_date = models.DateField('Дата последней активности', null=True, blank=True)
    weekly_xp = models.PositiveIntegerField('XP за текущую неделю', default=0)
    max_xp_day = models.PositiveIntegerField('Максимум XP за день', default=0)
    best_league_rank = models.PositiveIntegerField('Лучший результат в лиге (место)', null=True, blank=True)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)
    last_active = models.DateTimeField('Последняя активность', auto_now=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'

    def save(self, *args, **kwargs):
        new_level = 1
        xp = self.total_points
        for level, (xp_min, xp_max) in LEVEL_XP_BOUNDS.items():
            if xp_min <= xp <= xp_max:
                new_level = level
                break
            elif xp > xp_max:
                new_level = level + 1
        self.level = new_level
        super().save(*args, **kwargs)


class League(models.Model):
    name = models.CharField('Название лиги', max_length=50)
    tatar_name = models.CharField('Название на татарском', max_length=50)
    rank_order = models.PositiveIntegerField('Порядок (1 - низшая)', unique=True)
    min_users = models.PositiveIntegerField('Минимум пользователей для создания', default=10)
    max_users = models.PositiveIntegerField('Максимум пользователей', default=30)

    class Meta:
        ordering = ['rank_order']

    def __str__(self):
        return self.tatar_name


class LeagueInstance(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='instances')
    instance_number = models.PositiveIntegerField('Номер копии')
    current_week_start = models.DateField('Начало текущей недели', default=timezone.now)

    class Meta:
        unique_together = ['league', 'instance_number']

    def __str__(self):
        return f'{self.league.tatar_name} #{self.instance_number}'


class UserLeagueMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='league_memberships')
    league_instance = models.ForeignKey(LeagueInstance, on_delete=models.CASCADE)
    week_start = models.DateField()
    weekly_xp = models.PositiveIntegerField('XP за неделю', default=0)
    rank = models.PositiveIntegerField('Место в лиге', null=True, blank=True)
    promotion_to = models.ForeignKey(LeagueInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='promoted_from')
    relegation_to = models.ForeignKey(LeagueInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='relegated_from')

    class Meta:
        unique_together = ['user', 'week_start']

    def __str__(self):
        return f'{self.user.username} - {self.league_instance} - неделя {self.week_start}'


class SeasonalEvent(models.Model):
    name = models.CharField('Название', max_length=100)
    tatar_name = models.CharField('Название на татарском', max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    bonus_xp = models.PositiveIntegerField('Бонус XP за урок', default=0)
    bonus_coins = models.PositiveIntegerField('Бонус монет', default=0)

    def __str__(self):
        return self.tatar_name


class AchievementLevel(models.Model):
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='levels')
    level = models.PositiveIntegerField('Номер уровня')
    required_value = models.PositiveIntegerField('Необходимое значение')
    points_reward = models.PositiveIntegerField('Награда XP', default=50)
    coin_reward = models.PositiveIntegerField('Награда монет', default=20)
    tulip_reward = models.PositiveIntegerField('Награда тюльпанов', default=0)
    icon_class = models.CharField('Иконка', max_length=50, blank=True)

    class Meta:
        ordering = ['achievement', 'level']
        unique_together = ['achievement', 'level']

    def __str__(self):
        return f'{self.achievement.name} ур.{self.level}'


class AchievementProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_progress')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    current_value = models.PositiveIntegerField('Текущее значение', default=0)
    current_level = models.PositiveIntegerField('Достигнутый уровень', default=0)
    achieved_at = models.DateTimeField('Дата последнего получения', null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'achievement']

    def __str__(self):
        return f'{self.user.username} - {self.achievement.name}'

    def check_and_update(self):
        levels = self.achievement.levels.all()
        if not levels:
            return False
        current_max_level = self.current_level
        for level_obj in levels:
            if level_obj.level > current_max_level and self.current_value >= level_obj.required_value:
                profile = self.user.profile
                profile.total_points += level_obj.points_reward
                profile.coins += level_obj.coin_reward
                profile.tulips += level_obj.tulip_reward
                profile.save()
                self.current_level = level_obj.level
                self.achieved_at = timezone.now()
                self.save()
                return True
        return False


class ShopItem(models.Model):
    ITEM_TYPES = [
        ('streak_protect', 'Тумар защиты (защита ударного темпа)'),
        ('xp_boost', 'Курай-ускоритель (удвоение XP на 10 минут)'),
        ('retry_boost', 'Чак-чак энергии (восстановление попыток теста)'),
        ('golden_skullcap', 'Золотая тюбетейка (доступ к супер-тесту)'),
        ('clan_bet', 'Спор батыра (удвоение монет за 7 дней)'),
    ]
    name = models.CharField('Название', max_length=100)
    tatar_name = models.CharField('Название на татарском', max_length=100)
    item_type = models.CharField('Тип', max_length=20, choices=ITEM_TYPES)
    price_coins = models.PositiveIntegerField('Цена (монеты)', default=0)
    price_tulips = models.PositiveIntegerField('Цена (тюльпаны)', default=0)
    duration_minutes = models.PositiveIntegerField('Длительность эффекта (мин)', null=True, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    icon_class = models.CharField('Иконка', max_length=50, default='fas fa-box')

    def __str__(self):
        return self.tatar_name


class UserInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(ShopItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField('Количество', default=1)
    expires_at = models.DateTimeField('Действителен до', null=True, blank=True)
    used_at = models.DateTimeField('Активирован', null=True, blank=True)

    def is_active(self):
        return self.expires_at is None or self.expires_at > timezone.now()


class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    start_date = models.DateTimeField('Дата начала')
    end_date = models.DateTimeField('Дата окончания')
    is_auto_renew = models.BooleanField('Автопродление', default=False)
    is_active = models.BooleanField('Активна', default=True)

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()


class DailyRewardLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField('Дата')
    claimed = models.BooleanField('Выдано', default=False)
    streak_bonus = models.PositiveIntegerField('Бонус за стрик', default=5)

    class Meta:
        unique_together = ['user', 'date']


# Сигналы для автоматического создания профиля
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()