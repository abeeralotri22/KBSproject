from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, Prefetch, When, Case, IntegerField, OuterRef, Subquery, Q
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from graph_engine.ocr.ocr_extract import extract_text_from_image
from django.shortcuts import get_object_or_404
from . import models
from .models import CustomUser, Subject, Lesson, Story
from .serializers import RegisterSerializer, UpdateProfileSerializer, UserProfileSerializer, ChangePasswordSerializer, \
    SubjectSerializer, UserSubjectsSerializer, CreateLessonSerializer, LessonSerializer, AdminLessonListSerializer, \
    LessonWithStoriesSerializer, AdminLessonDetailSerializer, AdminUserDetailSerializer, TopUserSerializer, \
    ForgotPasswordSerializer, ReviewStorySerializer, StorySerializer


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



@api_view(['PATCH'])
@permission_classes([AllowAny]) # AllowAny because they forgot their password
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "Password reset successfully. You can now log in."
        }, status=status.HTTP_200_OK)

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
    # cache_key = "all_active_subjects"
    # cached_data = cache.get(cache_key)

    # if cached_data is not None:
    #     return Response(cached_data, status=status.HTTP_200_OK)
    subjects = Subject.objects.filter(is_active=True)
    serializer = SubjectSerializer(subjects, many=True)
    response_data = {
        "message": "Subjects fetched successfully",
        "subjects": serializer.data
    }
    # cache.set(cache_key, response_data, timeout=86400)
    return Response(response_data, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAdminUserRole])
def admin_get_subjects(request):
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



@api_view(['PATCH'])
@permission_classes([IsAdminUserRole])
def admin_toggle_subject_status(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)
    subject.is_active = not subject.is_active
    subject.save()
    cache.delete("all_active_subjects")
    status_message = "activated" if subject.is_active else "deactivated"
    return Response({
        "message": f"Subject {status_message} successfully",
        "subject": {
            "id": subject.id,
            "name": subject.name,
            "is_active": subject.is_active
        }
    }, status=status.HTTP_200_OK)


#Lesson
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_lesson(request):
    serializer = CreateLessonSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        lesson = serializer.save(user=request.user)
        response_serializer = LessonSerializer(lesson)

        return Response({
            "message": "Lesson added successfully",
            "lesson": response_serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def add_lesson_from_ocr(request):
    image = request.FILES.get('image')
    subject_id = request.data.get('subject_id')
    order = request.data.get('order', 0)

    if not image:
        return Response(
            {"error": "Please upload an image."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not subject_id:
        return Response(
            {"error": "Please provide subject_id."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {"error": "Subject not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        text = extract_text_from_image(image)
    except Exception as e:
        return Response(
            {
                "error": "OCR processing failed.",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    if not text:
        return Response(
            {"error": "No text was extracted from the image."},
            status=status.HTTP_400_BAD_REQUEST
        )

    lesson = Lesson.objects.create(
        content=text,
        order=order,
        user=request.user,
        subject=subject
    )

    serializer = LessonSerializer(lesson)

    return Response(
        {
            "message": "Lesson created successfully from OCR.",
            "lesson": serializer.data
        },
        status=status.HTTP_201_CREATED
    )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def review_story(request, story_id):
    try:
        with transaction.atomic():
            story = Story.objects.select_related('lesson__user').select_for_update().get(id=story_id)
            if story.lesson.user != request.user:
                return Response({"error": "You do not have permission to review this story."},
                                status=status.HTTP_403_FORBIDDEN)
            serializer = ReviewStorySerializer(story, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message": "Story reviewed successfully.",
                    "story": serializer.data
                }, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Story.DoesNotExist:
        return Response({"error": "Story not found."}, status=status.HTTP_404_NOT_FOUND)

#History
def get_user_subjects_history(request):
    subjects = Subject.objects.filter(lessons__user=request.user).distinct().order_by('name')
    serializer = SubjectSerializer(subjects, many=True)
    return Response({"message": "Subjects fetched successfully.",
                     "subjects": serializer.data},status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subject_detail_history(request, subject_id):
    if not request.user.subjects.filter(id=subject_id).exists():
        return Response({"error": "Subject not found or you are not enrolled in it."}, status=status.HTTP_404_NOT_FOUND)
    lessons = Lesson.objects.filter(
        user=request.user,
        subject_id=subject_id).prefetch_related('stories').order_by('order', 'created_at')
    paginator = UserPagination()
    paginated_lessons = paginator.paginate_queryset(lessons, request)
    serializer = LessonWithStoriesSerializer(paginated_lessons, many=True)
    return paginator.get_paginated_response({
        "message": "Subject lessons and stories fetched successfully.",
        "lessons": serializer.data
    })


#favorite
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_favorite_stories(request):
    favorites = Story.objects.filter(
        lesson__user=request.user,
        is_favorite=True
    ).order_by('-created_at')

    paginator = UserPagination()
    paginated_favorites = paginator.paginate_queryset(favorites, request)
    serializer = StorySerializer(paginated_favorites, many=True)
    return paginator.get_paginated_response({
        "message": "Favorites fetched successfully.",
        "favorites": serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_favorites(request, story_id):
    updated_count = Story.objects.filter(id=story_id, lesson__user=request.user).update(is_favorite=True)
    if updated_count == 0:
        return Response({"error": "Story not found."}, status=status.HTTP_404_NOT_FOUND)

    return Response({"message": "Story added to favorites."}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_favorites(request, story_id):
    updated_count = Story.objects.filter(id=story_id, lesson__user=request.user).update(is_favorite=False)
    if updated_count == 0:
        return Response({"error": "Story not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"message": "Story added to favorites."}, status=status.HTTP_200_OK)




##############Admin Section
@api_view(['GET'])
@permission_classes([IsAdminUserRole])
def get_all_users(request):
    users = CustomUser.objects.filter(role='customer').order_by('-date_joined')
    first_name = request.query_params.get('first_name')
    if first_name:
        users = users.filter(first_name__icontains=first_name)
    last_name = request.query_params.get('last_name')
    if last_name:
        users = users.filter(last_name__icontains=last_name)
    email = request.query_params.get('email')
    if email:
        users = users.filter(email__icontains=email)
    is_active_param = request.query_params.get('is_active')
    if is_active_param is not None:
        if is_active_param.lower() in ['true', '1', 'yes']:
            users = users.filter(is_active=True)
        elif is_active_param.lower() in ['false', '0', 'no']:
            users = users.filter(is_active=False)

    paginator = UserPagination()
    paginated_users = paginator.paginate_queryset(users, request)
    serializer = UserProfileSerializer(paginated_users, many=True)

    return paginator.get_paginated_response({
        "message": "Users fetched successfully",
        "total_users": users.count(),
        "users": serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAdminUserRole])
def admin_get_user_detail(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id, role='customer')
    except CustomUser.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    lessons_qs = Lesson.objects.filter(user=user).annotate(
        total_stories=Count('stories')
    ).prefetch_related(
        Prefetch('stories', queryset=Story.objects.order_by('-created_at')),
        'subject'
    ).order_by('-created_at')

    subject_id = request.query_params.get('subject_id')
    if subject_id:
        try:
            lessons_qs = lessons_qs.filter(subject_id=int(subject_id))
        except ValueError:
            return Response({"error": "Invalid subject_id format"}, status=status.HTTP_400_BAD_REQUEST)

    user = CustomUser.objects.filter(id=user_id).prefetch_related(
        Prefetch('lessons', queryset=lessons_qs)
    ).first()

    serializer = AdminUserDetailSerializer(user)
    return Response({
        "message": "User details fetched successfully",
        "user": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAdminUserRole])
def toggle_customer_status(request, user_id):
    is_active = request.data.get('is_active')
    if is_active is None or not isinstance(is_active, bool):
        return Response({"error": "Please provide a valid boolean 'is_active'."}, status=status.HTTP_400_BAD_REQUEST)
    updated_count = CustomUser.objects.filter(id=user_id, role='customer').update(is_active=is_active)
    if updated_count == 0:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    status_message = "activated" if is_active else "deactivated"
    return Response({
        "message": f"Customer {status_message} successfully",
        "user": {
            "id": user_id,
            "is_active": is_active
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
        cache.delete("all_active_subjects")
        return Response({
            "message": "Subject created successfully",
            "subject": serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)





@api_view(['PATCH'])
@permission_classes([IsAdminUserRole])
def admin_toggle_subject_status(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject.is_active = not subject.is_active
    subject.save()
    status_text = "activated" if subject.is_active else "deactivated"
    message = f"Subject {status_text} successfully"

    if not subject.is_active and subject.lessons.count() > 0:
        message += f" ({subject.lessons.count()} associated lesson(s) are now hidden)"

    return Response({
        "message": message,
        "is_active": subject.is_active
    }, status=status.HTTP_200_OK)





@api_view(['GET'])
@permission_classes([IsAdminUserRole])
def admin_get_all_lessons(request):
    lessons = Lesson.objects.annotate(total_stories=Count('stories')).order_by('-created_at')
    lessons = lessons.prefetch_related(
        Prefetch('stories', queryset=Story.objects.order_by('-created_at')),
        'user',
        'subject'
    )

    paginator = UserPagination()
    paginated_lessons = paginator.paginate_queryset(lessons, request)
    serializer = AdminLessonListSerializer(paginated_lessons, many=True)
    return paginator.get_paginated_response({
        "message": "Lessons fetched successfully",
        "lessons": serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAdminUserRole])
def admin_get_lesson_detail(request, lesson_id):
    try:
        lesson = Lesson.objects.select_related('user', 'subject').prefetch_related('stories').get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response({"error": "Lesson not found"}, status=status.HTTP_404_NOT_FOUND)
    serializer = AdminLessonDetailSerializer(lesson)
    return Response({
        "message": "Lesson details fetched successfully",
        "lesson": serializer.data
    }, status=status.HTTP_200_OK)





@api_view(['GET'])
@permission_classes([IsAdminUserRole])
@cache_page(60 * 5)
def admin_story_statistics(request):
    total_stories = Story.objects.count()
    subject_stats = Story.objects.values('lesson__subject__name').annotate(story_count=Count('id')).order_by('-story_count')
    stories_by_subject = {
        item['lesson__subject__name'].lower(): item['story_count']
        for item in subject_stats
    }
    return Response({
        "message": "Statistics fetched successfully",
        "total_stories": total_stories,
        "stories_by_subject": stories_by_subject
    }, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAdminUserRole])
@cache_page(60 * 5)
def admin_subject_ratings_stats(request):
    subjects = Subject.objects.filter(is_active=True).annotate(
        total_stories=Count('lessons__stories'),
        rating_5=Count(Case(When(lessons__stories__initial_rating=5, then=1), output_field=IntegerField())),
        rating_4=Count(Case(When(lessons__stories__initial_rating=4, then=1), output_field=IntegerField())),
        rating_3=Count(Case(When(lessons__stories__initial_rating=3, then=1), output_field=IntegerField())),
        rating_2=Count(Case(When(lessons__stories__initial_rating=2, then=1), output_field=IntegerField())),
        rating_1=Count(Case(When(lessons__stories__initial_rating=1, then=1), output_field=IntegerField()))).order_by('name')

    data = []
    for subject in subjects:
        data.append({
            "name": subject.name.lower(),
            "total_stories": subject.total_stories,
            "ratings": {
                "5": subject.rating_5,
                "4": subject.rating_4,
                "3": subject.rating_3,
                "2": subject.rating_2,
                "1": subject.rating_1
            }
        })

    return Response({
        "message": "Subject ratings statistics fetched successfully",
        "subjects": data
    }, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAdminUserRole])
@cache_page(60 * 5)
def admin_top_users(request):
    first_story_subquery = Story.objects.filter(lesson=OuterRef('pk')).order_by('created_at').values('pk')[:1]
    lessons_with_first_story = Lesson.objects.annotate( first_story_id=Subquery(first_story_subquery)).exclude(first_story_id__isnull=True)
    top_users = CustomUser.objects.filter(role='customer').annotate(
        total_first_stories=Count(
            'lessons__pk',
            filter=Q(lessons__pk__in=lessons_with_first_story.values('pk'))
        )).order_by('-total_first_stories')[:3] # Sort highest to lowest, limit to 3

    serializer = TopUserSerializer(top_users, many=True)
    return Response({
        "message": "Top 3 users fetched successfully",
        "top_users": serializer.data
    }, status=status.HTTP_200_OK)


