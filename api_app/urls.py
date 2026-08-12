from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # register & login
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),

    # built-in
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Profile
    path('profile/', views.update_profile, name='update profile'),
    path('get_profile/', views.get_profile, name='get profile'),
    path('change_password/', views.change_password, name='change the password'),

    # admin
    path('users/all/', views.get_all_users, name='get_all_users'),
    path('users/<int:user_id>/toggle-status/', views.toggle_customer_status, name='toggle_customer_status'),
]
