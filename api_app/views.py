from django.contrib.auth import authenticate
from django.shortcuts import render

import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, UpdateProfileSerializer, UserProfileSerializer,ChangePasswordSerializer


# auth_logger = logging.getLogger('service.auth')

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data= request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Registered successfully.",
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }, status=status.HTTP_201_CREATED)

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(username=email, password=password)

    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": f"logged in successfully",
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }, status=status.HTTP_200_OK)

    return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    user = request.user
    serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Profile updated successfully",
            "user": serializer.data
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    serializer = UserProfileSerializer(request.user)

    return Response({
        "message": "Profile fetched successfully",
        "user": serializer.data
    }, status=status.HTTP_200_OK)




@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Password changed successfully."
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

