from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from django.urls import reverse
import json
from .services.mistral_service import MistralService
from .models import (
    Course, Community, Achievement, Lesson, Question, LessonCompletion, Profile,
    League, LeagueInstance, UserLeagueMembership, SeasonalEvent, AchievementLevel,
    AchievementProgress, ShopItem, UserInventory, UserSubscription, DailyRewardLog,
    LEVEL_XP_BOUNDS
)

mistral_service = MistralService()


# ---------- СУЩЕСТВУЮЩИЕ VIEW ----------
def home(request):
    courses = Course.objects.filter(status='published').order_by('order', '-created_at')
    communities = Community.objects.filter(is_active=True).order_by('order', 'name')
    achievements = Achievement.objects.filter(is_active=True)
    context = {
        'courses': courses,
        'communities': communities,
        'achievements': achievements,
    }
    return render(request, 'index.html', context)


def education(request):
    courses = Course.objects.filter(status='published').order_by('order', '-created_at')
    return render(request, 'education.html', {'courses': courses})


def community(request):
    communities = Community.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'community.html', {'communities': communities})


def ratings(request):
    return HttpResponse("Рейтинги учеников - в разработке")


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            messages.error(request, 'Пароли не совпадают')
            return redirect('register')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            return redirect('register')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            return redirect('register')
        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        messages.success(request, 'Регистрация успешно завершена!')
        return redirect('home')
    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    list(messages.get_messages(request))
    return redirect('home')


@login_required
def profile_view(request):
    achievements = Achievement.objects.filter(is_active=True)
    return render(request, 'profile.html', {
        'user': request.user,
        'achievements': achievements
    })


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])
        if not user_message:
            return JsonResponse({'error': 'Сообщение не может быть пустым'}, status=400)
        result = mistral_service.get_response(user_message, conversation_history)
        if result['success']:
            return JsonResponse({'response': result['response'], 'history': result['history']})
        else:
            return JsonResponse({'error': result['error']}, status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Внутренняя ошибка сервера: {str(e)}'}, status=500)


def all_courses(request):
    courses = Course.objects.filter(status='published').order_by('order', '-created_at')
    return render(request, 'courses.html', {'courses': courses})


def all_communities(request):
    communities = Community.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'communities.html', {'communities': communities})


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, status='published')
    lessons = course.lessons.all().order_by('order')
    completed_lessons = set()
    if request.user.is_authenticated:
        completed_lessons = set(
            LessonCompletion.objects.filter(user=request.user, lesson__course=course).values_list('lesson_id',
                                                                                                  flat=True))
    unlocked_lessons = set()
    if request.user.is_authenticated:
        unlocked_lessons.update(completed_lessons)
        first_lesson = lessons.first()
        if first_lesson and first_lesson.id not in completed_lessons:
            unlocked_lessons.add(first_lesson.id)
        last_completed = None
        for lesson in lessons:
            if lesson.id in completed_lessons:
                last_completed = lesson
        if last_completed:
            next_lesson = Lesson.objects.filter(course=course, order=last_completed.order + 1).first()
            if next_lesson and next_lesson.id not in completed_lessons:
                unlocked_lessons.add(next_lesson.id)
    else:
        if lessons:
            unlocked_lessons.add(lessons[0].id)
    total_lessons = course.lessons_count
    completed_count = len(completed_lessons)
    progress_percent = (completed_count / total_lessons) * 100 if total_lessons > 0 else 0
    context = {
        'course': course,
        'lessons': lessons,
        'completed_lessons': completed_lessons,
        'unlocked_lessons': unlocked_lessons,
        'progress_percent': round(progress_percent, 1),
    }
    return render(request, 'course_detail.html', context)


def check_lesson_access(user, lesson):
    if not user.is_authenticated:
        return lesson.order == 1
    if lesson.order == 1:
        return True
    previous_lesson = Lesson.objects.filter(course=lesson.course, order=lesson.order - 1).first()
    if previous_lesson:
        return LessonCompletion.objects.filter(user=user, lesson=previous_lesson).exists()
    return False


@login_required
def lesson_detail(request, course_slug, order):
    course = get_object_or_404(Course, slug=course_slug, status='published')
    lesson = get_object_or_404(Lesson, course=course, order=order)
    if not check_lesson_access(request.user, lesson):
        messages.error(request, 'Этот урок ещё не доступен. Пройдите предыдущие уроки.')
        return redirect('course_detail', slug=course.slug)
    has_test = lesson.questions.exists()
    is_completed = LessonCompletion.objects.filter(user=request.user, lesson=lesson).exists()
    context = {
        'course': course,
        'lesson': lesson,
        'has_test': has_test,
        'is_completed': is_completed,
    }
    return render(request, 'lesson_detail.html', context)


@login_required
def take_test(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if not check_lesson_access(request.user, lesson):
        messages.error(request, 'Этот урок ещё не доступен.')
        return redirect('course_detail', slug=lesson.course.slug)
    questions = lesson.questions.all()
    if not questions.exists():
        messages.error(request, 'Для этого урока ещё нет теста.')
        return redirect('lesson_detail', course_slug=lesson.course.slug, order=lesson.order)
    context = {'lesson': lesson, 'questions': questions}
    return render(request, 'test_duo.html', context)


@login_required
def check_answer_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = json.loads(request.body)
    question_id = data.get('question_id')
    selected = data.get('selected')
    answer_text = data.get('answer_text', '').strip()
    question = get_object_or_404(Question, id=question_id)
    is_correct = False
    if question.question_type == 'translate':
        correct_text = question.option1.strip().lower()
        is_correct = (answer_text.lower() == correct_text)
    else:
        if selected and selected == question.correct_option:
            is_correct = True
    return JsonResponse({'correct': is_correct, 'explanation': question.explanation})


@login_required
def submit_test(request, lesson_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not check_lesson_access(request.user, lesson):
        messages.error(request, 'Этот урок ещё не доступен.')
        return redirect('course_detail', slug=lesson.course.slug)

    questions = list(lesson.questions.all())
    total_questions = len(questions)

    # Подсчёт правильных ответов
    correct_count = 0
    for question in questions:
        answer_key = f'question_{question.id}'
        selected_option = request.POST.get(answer_key)
        if selected_option and int(selected_option) == question.correct_option:
            correct_count += 1

    # Вычисляем процент
    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

    # ВСЕГДА сохраняем прохождение, даже если процент ниже 70
    completion, created = LessonCompletion.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'test_score': percentage}
    )

    # Обновляем процент, если он стал выше
    if not created and completion.test_score < percentage:
        completion.test_score = percentage
        completion.save()

    # Начисляем награды ТОЛЬКО за первое прохождение (независимо от процента)
    if created:
        profile = request.user.profile
        profile.total_points += 150
        profile.coins += 50
        profile.lessons_completed += 1
        profile.save()
        messages.success(request, f'🎉 Урок пройден! +150 очков опыта, +50 монет.')
    else:
        messages.info(request, f'Тест пройден повторно. Результат: {percentage:.0f}%')

    # Перенаправляем на страницу курса, чтобы показать разблокированные уроки
    return redirect('course_detail', slug=lesson.course.slug)


def find_or_create_league_instance_for_user(user):
    league = League.objects.filter(rank_order=1).first()
    if not league:
        league = League.objects.create(name='Начинающий', tatar_name='Башлангыч', rank_order=1)
    instance, _ = LeagueInstance.objects.get_or_create(league=league, instance_number=1)
    return instance


@login_required
def league_table(request):
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    membership = UserLeagueMembership.objects.filter(user=request.user, week_start=week_start).first()
    if not membership:
        messages.info(request, 'Вы ещё не попали в лигу. Пройдите несколько уроков.')
        return redirect('profile')
    league_instance = membership.league_instance
    all_members = UserLeagueMembership.objects.filter(league_instance=league_instance, week_start=week_start).order_by(
        '-weekly_xp')
    for idx, m in enumerate(all_members, start=1):
        m.rank = idx
    user_rank = next((idx for idx, m in enumerate(all_members, start=1) if m.user == request.user), None)
    context = {
        'league_instance': league_instance,
        'members': all_members,
        'user_rank': user_rank,
        'week_start': week_start,
    }
    return render(request, 'league.html', context)


@login_required
def shop(request):
    items = ShopItem.objects.filter(is_active=True)
    user_inventory = UserInventory.objects.filter(user=request.user, used_at__isnull=True)
    return render(request, 'shop.html', {'items': items, 'inventory': user_inventory})


@login_required
def purchase_item(request, item_id):
    item = get_object_or_404(ShopItem, id=item_id, is_active=True)
    profile = request.user.profile
    if item.price_coins > 0 and profile.coins >= item.price_coins:
        profile.coins -= item.price_coins
        profile.save()
        expires_at = None
        if item.duration_minutes:
            expires_at = timezone.now() + timedelta(minutes=item.duration_minutes)
        UserInventory.objects.create(
            user=request.user,
            item=item,
            quantity=1,
            expires_at=expires_at
        )
        messages.success(request, f'Вы купили {item.tatar_name}!')
    elif item.price_tulips > 0 and profile.tulips >= item.price_tulips:
        profile.tulips -= item.price_tulips
        profile.save()
        UserInventory.objects.create(user=request.user, item=item, quantity=1)
        messages.success(request, f'Вы купили {item.tatar_name}!')
    else:
        messages.error(request, 'Недостаточно средств.')
    return redirect('shop')


@login_required
def use_item(request, inventory_id):
    inv_item = get_object_or_404(UserInventory, id=inventory_id, user=request.user, used_at__isnull=True)
    item = inv_item.item
    if item.item_type == 'streak_protect':
        request.session['streak_protect_active'] = True
        messages.success(request, 'Тумар защиты активирован! При пропуске дня стрик не сбросится.')
    elif item.item_type == 'xp_boost':
        request.session['xp_boost_until'] = (timezone.now() + timedelta(minutes=item.duration_minutes)).isoformat()
        messages.success(request, f'Курай-ускоритель активирован на {item.duration_minutes} мин!')
    else:
        messages.info(request, 'Этот предмет пока нельзя использовать.')
    inv_item.used_at = timezone.now()
    inv_item.save()
    return redirect('shop')


@login_required
def achievements_list(request):
    achievements = Achievement.objects.prefetch_related('levels').all()
    user_progress = {ap.achievement_id: ap for ap in AchievementProgress.objects.filter(user=request.user)}
    from django.template.defaulttags import register
    @register.filter
    def get_item(dictionary, key):
        return dictionary.get(key)

    context = {
        'achievements': achievements,
        'user_progress': user_progress,
    }
    return render(request, 'achievements.html', context)


def check_achievements_on_lesson_complete(user, lesson):
    profile = user.profile
    ach = Achievement.objects.filter(name='Первый шаг').first()
    if ach and profile.lessons_completed >= 1:
        update_achievement_progress(user, ach, 1)
    ach = Achievement.objects.filter(name='Прилежный ученик').first()
    if ach:
        update_achievement_progress(user, ach, profile.lessons_completed)
    ach = Achievement.objects.filter(name='Идеальный порядок').first()
    if ach:
        update_achievement_progress(user, ach, profile.streak_days)
    completions = LessonCompletion.objects.filter(user=user, test_score__gte=90).count()
    ach = Achievement.objects.filter(name='Снайпер').first()
    if ach:
        update_achievement_progress(user, ach, completions)
    ach = Achievement.objects.filter(name='Золотое усердие').first()
    if ach:
        update_achievement_progress(user, ach, profile.total_points)


def update_achievement_progress(user, achievement, current_value):
    progress, created = AchievementProgress.objects.get_or_create(user=user, achievement=achievement)
    if current_value > progress.current_value:
        progress.current_value = current_value
        progress.save()
        progress.check_and_update()