from django.contrib.auth import authenticate
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from . import models
from .models import CustomUser, Subject
from .serializers import RegisterSerializer, UpdateProfileSerializer, UserProfileSerializer, ChangePasswordSerializer, \
    SubjectSerializer,UserSubjectsSerializer


class IsAdminUserRole(permissions.BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')



######### Registration and Profile
class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

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
                "first_name" : user.first_name,
                "last_name" : user.last_name,
                "role":user.role
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
                "role":user.role
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



##############Sujects, Lessons and Stories
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subjects(request):
    subjects = Subject.objects.all()
    serializer = SubjectSerializer(subjects, many=True)
    return Response({
        "message": "Subjects fetched successfully",
        "subjects": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chosen_subjects(request):
    user = request.user
    serializer = UserSubjectsSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        subjects_data = SubjectSerializer(user.subjects, many=True).data
        return Response({
            "message": "Subjects selected successfully",
            "selected_subjects": subjects_data
        }, status=status.HTTP_200_OK)

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)






##############Admin Section
@api_view(['GET'])
@permission_classes([IsAdminUserRole])
def get_all_users(request):
    users = CustomUser.objects.filter(role = 'customer').order_by('-date_joined')
    search = request.query_params.get('search')
    if search:
        users = users.filter(
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(email__icontains=search)
        )

    paginator = UserPagination()
    paginated_users = paginator.paginate_queryset(users, request)
    serializer = UserProfileSerializer(paginated_users, many=True)

    return paginator.get_paginated_response({
        "message": "Users fetched successfully",
        "total_users": users.count(),
        "users": serializer.data
    })


@api_view(['PATCH'])
@permission_classes([IsAdminUserRole])
def toggle_customer_status(request, user_id):
    customer = CustomUser.objects.get(id=user_id, role='customer')
    is_active = request.data.get('is_active')
    if is_active is None:
        return Response({
            "error": "Please provide 'is_active' field (true/false)"
        }, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(is_active, bool):
        return Response({
            "error": "'is_active' must be a boolean (true/false)"
        }, status=status.HTTP_400_BAD_REQUEST)
    customer.is_active = is_active
    customer.save()
    status_message = "activated" if is_active else "deactivated"
    return Response({
        "message": f"Customer {status_message} successfully",
        "user": {
            "id": customer.id,
            "email": customer.email,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "is_active": customer.is_active
        }
    }, status=status.HTTP_200_OK)


#Subjects
@api_view(['POST'])
@permission_classes([IsAdminUserRole])
@parser_classes([MultiPartParser, FormParser]) # Required for image upload
def admin_create_subject(request):
    serializer = SubjectSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Subject created successfully",
            "subject": serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAdminUserRole])
def admin_delete_subject(request, subject_id):
    """
    This will also delete all lessons associated with this subject.
    """
    subject = Subject.objects.get(id=subject_id)
    if not subject:
        return Response({
            "error": "Subject not found"
        }, status=status.HTTP_404_NOT_FOUND)
    lesson_count = subject.lessons.count()
    subject.delete()
    message = "Subject deleted successfully"
    if lesson_count > 0:
        message += f" (along with {lesson_count} associated lesson(s))"
    return Response({
        "message": message
    }, status=status.HTTP_200_OK)


