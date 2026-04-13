from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
import json
from .services.mistral_service import MistralService
from .models import Course, Community, Achievement, Lesson, Question, LessonCompletion

mistral_service = MistralService()


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
    messages.success(request, 'Вы вышли из аккаунта')
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
        completed_lessons = set(LessonCompletion.objects.filter(user=request.user, lesson__course=course).values_list('lesson_id', flat=True))

    # Определяем доступные уроки:
    # - пройденные уроки всегда доступны
    # - первый урок доступен всегда
    # - следующий за последним пройденным тоже доступен
    unlocked_lessons = set()
    if request.user.is_authenticated:
        # Все пройденные уроки разблокированы
        unlocked_lessons.update(completed_lessons)
        # Первый урок, если ещё не пройден, тоже разблокирован
        first_lesson = lessons.first()
        if first_lesson and first_lesson.id not in completed_lessons:
            unlocked_lessons.add(first_lesson.id)
        # Находим последний пройденный урок
        last_completed = None
        for lesson in lessons:
            if lesson.id in completed_lessons:
                last_completed = lesson
        # Если есть последний пройденный, разблокируем следующий за ним (если он существует и не пройден)
        if last_completed:
            next_lesson = Lesson.objects.filter(course=course, order=last_completed.order + 1).first()
            if next_lesson and next_lesson.id not in completed_lessons:
                unlocked_lessons.add(next_lesson.id)
    else:
        # Неавторизованные видят только первый урок
        if lessons:
            unlocked_lessons.add(lessons[0].id)

    # Прогресс в процентах по количеству пройденных уроков
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
    """Проверяет, доступен ли урок пользователю (последовательно)"""
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
    return render(request, 'test.html', context)


@login_required
def submit_test(request, lesson_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    lesson = get_object_or_404(Lesson, id=lesson_id)

    if not check_lesson_access(request.user, lesson):
        messages.error(request, 'Этот урок ещё не доступен.')
        return redirect('course_detail', slug=lesson.course.slug)

    questions = lesson.questions.all()
    correct_count = 0
    results = []

    for question in questions:
        answer_key = f'question_{question.id}'
        selected_option = request.POST.get(answer_key)
        is_correct = False
        if selected_option and int(selected_option) == question.correct_option:
            correct_count += 1
            is_correct = True
        results.append({
            'question': question.text,
            'selected_option': selected_option,
            'correct_option': question.correct_option,
            'is_correct': is_correct,
            'explanation': question.explanation,
            'options': [question.option1, question.option2, question.option3, question.option4]
        })

    total_questions = questions.count()
    percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    # Всегда сохраняем результат (даже если <70%)
    completion, created = LessonCompletion.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'test_score': percentage}
    )
    if not created and completion.test_score < percentage:
        completion.test_score = percentage
        completion.save()
        messages.info(request, f'Результат теста улучшен до {percentage:.0f}%')

    # Начисляем награды ТОЛЬКО при первом прохождении И если процент >= 70
    if percentage >= 70 and created:
        exp_points = 150
        coins = 50
        profile = request.user.profile
        profile.total_points += exp_points
        profile.coins += coins
        profile.lessons_completed += 1
        profile.save()
        messages.success(request, f'Урок пройден! +{exp_points} очков опыта, +{coins} монет.')
    elif percentage >= 70 and not created:
        messages.success(request, f'Тест пройден! (награды уже получены ранее)')
    else:
        messages.warning(request, f'Тест не пройден. Правильных ответов: {correct_count} из {total_questions} ({percentage:.0f}%). Нужно 70%.')

    context = {
        'lesson': lesson,
        'results': results,
        'correct_count': correct_count,
        'total_questions': total_questions,
        'percentage': percentage,
    }
    return render(request, 'test_result.html', context)