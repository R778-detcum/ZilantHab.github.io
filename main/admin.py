from django.contrib import admin
from django.utils.html import format_html
from .models import Course, Lesson, Community, Achievement, Profile, Question, LessonCompletion
from .models import League, LeagueInstance, UserLeagueMembership, SeasonalEvent, AchievementLevel, AchievementProgress, ShopItem, UserInventory, UserSubscription, DailyRewardLog

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'coins', 'tulips', 'level', 'streak_days', 'lessons_completed', 'created_at']
    search_fields = ['user__username', 'user__email']
    list_editable = ['coins', 'tulips']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'price_display', 'status', 'lessons_count', 'order', 'created_at']
    list_filter = ['status', 'level', 'is_free', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['order', 'status']
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Основная информация', {'fields': ('title', 'slug', 'description', 'short_description')}),
        ('Детали курса', {'fields': ('level', 'duration_weeks', 'lessons_count')}),
        ('Цена и акции', {'fields': ('price', 'old_price', 'is_free'), 'classes': ('collapse',)}),
        ('Визуальное оформление', {'fields': ('icon_class', 'badge_text', 'badge_color'), 'classes': ('collapse',)}),
        ('Статус и даты', {'fields': ('status', 'order', 'published_at'), 'classes': ('collapse',)}),
    )

    def price_display(self, obj):
        if obj.is_free:
            return format_html('<span style="color: green;">🔥 Бесплатно</span>')
        if obj.old_price:
            return format_html('<span style="text-decoration: line-through;">{} ₽</span> → <b>{} ₽</b>', obj.old_price, obj.price)
        return f'{obj.price} ₽'
    price_display.short_description = 'Цена'

    actions = ['make_published', 'make_draft']

    def make_published(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='published', published_at=timezone.now())
    make_published.short_description = 'Опубликовать выбранные курсы'

    def make_draft(self, request, queryset):
        queryset.update(status='draft')
    make_draft.short_description = 'Снять с публикации'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'section', 'order', 'duration_minutes', 'is_free_preview']
    list_filter = ['course', 'section', 'is_free_preview']
    search_fields = ['title', 'content']
    list_editable = ['order', 'duration_minutes']
    fieldsets = (
        ('Информация об уроке', {'fields': ('course', 'title', 'section', 'order', 'duration_minutes')}),
        ('Контент', {'fields': ('video_url', 'content', 'is_free_preview')}),
    )


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['name', 'member_count', 'is_active', 'order', 'icon_preview']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['order', 'member_count', 'is_active']

    def icon_preview(self, obj):
        return format_html('<i class="{}"></i>', obj.icon_class)
    icon_preview.short_description = 'Иконка'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['name', 'points', 'is_active', 'icon_preview']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['points', 'is_active']

    def icon_preview(self, obj):
        return format_html('<i class="{}"></i>', obj.icon_class)
    icon_preview.short_description = 'Иконка'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'lesson', 'correct_option']
    list_filter = ['lesson']
    search_fields = ['text']


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'test_score', 'completed_at']
    list_filter = ['lesson__course', 'lesson']
    search_fields = ['user__username', 'lesson__title']


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['tatar_name', 'rank_order', 'min_users', 'max_users']


@admin.register(LeagueInstance)
class LeagueInstanceAdmin(admin.ModelAdmin):
    list_display = ['league', 'instance_number', 'current_week_start']


@admin.register(UserLeagueMembership)
class UserLeagueMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'league_instance', 'week_start', 'weekly_xp', 'rank']


@admin.register(SeasonalEvent)
class SeasonalEventAdmin(admin.ModelAdmin):
    list_display = ['tatar_name', 'start_date', 'end_date', 'is_active']


@admin.register(AchievementLevel)
class AchievementLevelAdmin(admin.ModelAdmin):
    list_display = ['achievement', 'level', 'required_value', 'points_reward', 'coin_reward']


@admin.register(AchievementProgress)
class AchievementProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'current_value', 'current_level']


@admin.register(ShopItem)
class ShopItemAdmin(admin.ModelAdmin):
    list_display = ['tatar_name', 'item_type', 'price_coins', 'price_tulips', 'is_active']


@admin.register(UserInventory)
class UserInventoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'quantity', 'expires_at', 'used_at']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_date', 'end_date', 'is_active']


@admin.register(DailyRewardLog)
class DailyRewardLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'claimed', 'streak_bonus']