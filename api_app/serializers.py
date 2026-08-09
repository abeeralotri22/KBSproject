from rest_framework import serializers
from .models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password']

    def validate_email(self, value):
        value = value.lower()
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password
        )
        return user
