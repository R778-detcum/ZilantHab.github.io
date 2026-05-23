from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('education/', views.education, name='education'),
    path('community/', views.community, name='community'),
    path('ratings/', views.ratings, name='ratings'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('courses/', views.all_courses, name='all_courses'),
    path('communities/', views.all_communities, name='all_communities'),
    path('course/<slug:slug>/', views.course_detail, name='course_detail'),
    path('course/<slug:course_slug>/lesson/<int:order>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/test/', views.take_test, name='take_test'),
    path('lesson/<int:lesson_id>/test/submit/', views.submit_test, name='submit_test'),

    # Новые маршруты для лиг, магазина, достижений
    path('league/', views.league_table, name='league'),
    path('shop/', views.shop, name='shop'),
    path('shop/buy/<int:item_id>/', views.purchase_item, name='purchase_item'),
    path('shop/use/<int:inventory_id>/', views.use_item, name='use_item'),
    path('achievements/', views.achievements_list, name='achievements'),

    path('api/check-answer/', views.check_answer_ajax, name='check_answer_ajax'),

    # TTS для озвучки (если будете использовать)
    # path('tts/', views.tts, name='tts'),  # раскомментируйте, когда добавите функцию tts в views.py
]