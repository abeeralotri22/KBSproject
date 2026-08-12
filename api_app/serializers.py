from rest_framework import serializers
from .models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)


    class Meta:
        model = CustomUser
        fields = ['first_name','last_name','email', 'password']

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
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            first_name = first_name,
            last_name = last_name,
            password=password,
            role='customer'

        )
        return user

class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'profile_image']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'profile_image',
            'role'
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