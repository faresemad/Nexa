# apps/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("بيانات الدخول غير صحيحة")
        if user.status != "active":
            raise serializers.ValidationError("الحساب غير نشط")
        return {"user": user}


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "avatar_url", "global_role", "status"]
        read_only_fields = ["id", "global_role"]


class WorkspaceInfoSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    role = serializers.CharField()
    permissions = serializers.ListField(child=serializers.CharField())


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    workspaces = WorkspaceInfoSerializer(many=True)
