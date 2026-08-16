from django.urls import path
from . import views
from rest_framework_simplejwt.views import (TokenObtainPairView, TokenRefreshView)

urlpatterns = [
    # register & login
    path('register/', views.register, name='register'),###########
    path('login/', views.login, name='login'),
    path('forgot password/',views.forgot_password, name = 'forgot-password'),

    # built-in
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Profile
    path('profile/', views.update_profile, name='update profile'),
    path('get_profile/', views.get_profile, name='get profile'),
    path('change_password/', views.change_password, name='change the password'),############

    # Subjects For Customer
    path('subjects/all/', views.get_subjects, name='get_all_subjects'),
    path('subjects/choose/', views.chosen_subjects, name='choose'),

    #Lesson
    path('lesson/add/', views.add_lesson, name='adding_lesson'),
    path(
        'lesson/add-ocr/',
        views.add_lesson_from_ocr,
        name='adding_lesson_from_ocr'
    ),
    #history###############
    path('user/subjects/', views.get_user_subjects_history, name='user-subjects'),
    path('user/subjects/<int:subject_id>/', views.get_subject_detail_history, name='user-subject-detail'),

    #review#################
    path('stories/<int:story_id>/review/', views.review_story, name='review-story'),

    #favorite######################

    path('user/favorites/', views.get_favorite_stories, name='get-favorites'),
    path('user/favorites/<int:story_id>/add/', views.add_to_favorites, name='add-favorite'),
    path('user/favorites/<int:story_id>/remove/', views.remove_from_favorites, name='remove-favorite'),

    # admin
    path('users/all/', views.get_all_users, name='get_all_users'),
    path('users/<int:user_id>/details/', views.admin_get_user_detail, name='get_user_detail'),
    path('users/<int:user_id>/toggle-status/', views.toggle_customer_status, name='toggle_customer_status'),
    path('subjects/add/', views.admin_create_subject, name='admin_create_subject'),
    path('subjects/', views.admin_get_subjects, name='admin-get-subjects'),
    path('subjects/<int:subject_id>/delete/', views.admin_toggle_subject_status, name='admin_toggle_subject_status'),
    path('stories/', views.admin_get_all_lessons, name='get_all_lessons_and_stories'),
    path('stories/<int:lesson_id>/', views.admin_get_lesson_detail, name='get_lesson_details'),
    #statistics
    path('statistics/stories/', views.admin_story_statistics, name='admin_story_statistics'),
    path('statistics/rating/', views.admin_subject_ratings_stats, name='admin-subject-rating-stats'),
    path('statistics/top-users/', views.admin_top_users, name='admin-top-users'),

]
