from rest_framework import serializers
from .models import CustomUser, Subject, Lesson, Story


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password', 'security_code']

    def validate_email(self, value):
        value = value.lower()
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        security_code = validated_data['security_code']
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role='customer',
            security_code = security_code

        )
        return user



class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    security_key = serializers.IntegerField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        try:
            self.user = CustomUser.objects.get(email=value.lower())
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("No account found with this email.")
        return value

    def validate_security_key(self, value):
        if self.user.security_key != value:
            raise serializers.ValidationError("Invalid security key.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "Passwords do not match."})
        return attrs

    def save(self, **kwargs):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        return self.user



class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'profile_image']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'profile_image',
            'role',
            'security_code'
            'is_active'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        # set_password hashes the new password automatically
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


######### Subjects
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']


class UserSubjectsSerializer(serializers.ModelSerializer):
    subjects = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Subject.objects.all()
    )

    class Meta:
        model = CustomUser
        fields = ['subjects']

    def validate_subjects(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("You must select at least one subject.")
        if len(value) > 3:
            raise serializers.ValidationError("You cannot select more than 3 subjects.")
        return value


#Lesson
class LessonSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Lesson
        fields = ['id', 'subject', 'subject_name', 'content', 'order', 'created_at']


class CreateLessonSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())

    class Meta:
        model = Lesson
        fields = ['subject', 'content', 'order']

    def validate_subject(self, value):
        user = self.context['request'].user
        # to check if the chosen subject is in the user's enrolled subjects
        if value not in user.subjects.all():
            raise serializers.ValidationError(
                "You cannot add a lesson to this subject. Please select it first."
            )

        return value



#Story



class StorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ['id', 'title', 'content', 'initial_rating', 'review_comment', 'created_at']





class LessonWithStoriesSerializer(serializers.ModelSerializer):
    """ lesson with its stories"""
    stories = StorySerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Lesson
        fields = ['id', 'subject', 'subject_name', 'content', 'order', 'created_at', 'stories']


class UserLessonSummarySerializer(serializers.ModelSerializer):
    """Used inside User Detail to show first story and total count"""
    first_story = serializers.SerializerMethodField()
    total_stories = serializers.IntegerField(read_only=True)
    subject_id = serializers.IntegerField(read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Lesson
        fields = ['id', 'subject_id', 'subject_name', 'content', 'total_stories', 'first_story', 'created_at']

    def get_first_story(self, obj):
        stories_cache = obj.stories.all()[:1]
        if stories_cache:
            return FirstStorySerializer(stories_cache[0]).data
        return None


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Serializer for Admin viewing a specific Customer's profile and lessons"""
    lessons = UserLessonSummarySerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'profile_image',
            'security_code',
            'lessons'
        ]


####

class FirstStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ['id', 'title', 'content', 'initial_rating']
class AdminLessonListSerializer(serializers.ModelSerializer):
    """list of all lessons with the first story of each lesson"""
    first_story = serializers.SerializerMethodField()
    total_stories = serializers.IntegerField(read_only=True)  # Comes from view annotation
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id',
            'subject_name',
            'content',
            'total_stories',
            'first_story',
            'created_at'
        ]

    def get_first_story(self, obj):
        stories_cache = obj.stories.all()[:1]
        if stories_cache:
            return FirstStorySerializer(stories_cache[0]).data
        return None


class AdminLessonDetailSerializer(serializers.ModelSerializer):
    """Serializer for when the admin clicks on a specific lesson"""
    stories = StorySerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id',
            'subject_name',
            'content',
            'customer_name',
            'created_at',
            'stories'
        ]

    def get_customer_name(self, obj):
        first = obj.user.first_name or ""
        last = obj.user.last_name or ""
        full_name = f"{first} {last}".strip()
        return full_name if full_name else obj.user.email


class TopUserSerializer(serializers.ModelSerializer):
    total_first_stories = serializers.IntegerField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'profile_image', 'total_first_stories']


class ReviewStorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = ['initial_rating', 'review_comment']

    def validate_initial_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        rating = attrs.get('initial_rating')
        comment = attrs.get('review_comment')
        if rating is None and not comment:
            raise serializers.ValidationError({
                "detail": "You must provide at least a rating or a comment to submit a review."
            })

        return attrs
