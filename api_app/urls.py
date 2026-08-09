from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    #register & login
    path('register/', views.register, name='register'),
    path('login/', views.login, name = 'login'),
    #built-in
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    #Profile
    path('profile/', views.profile, name = 'profile')

]