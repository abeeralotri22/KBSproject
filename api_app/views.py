from django.contrib.auth import authenticate
from django.shortcuts import render

import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer

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





