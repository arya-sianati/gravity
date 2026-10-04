from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    level_start_xp = serializers.SerializerMethodField()
    next_level_xp = serializers.SerializerMethodField()
    level_progress = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'display_name',
            'total_xp',
            'current_level',
            'level_start_xp',
            'next_level_xp',
            'level_progress',
            'location_privacy_mode',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'total_xp',
            'current_level',
            'level_start_xp',
            'next_level_xp',
            'level_progress',
            'created_at',
            'updated_at',
        ]

    def get_level_start_xp(self, obj):
        from activities.logic.xp_service import xp_for_level
        return xp_for_level(obj.current_level)
        
    def get_next_level_xp(self, obj):
        from activities.logic.xp_service import xp_for_next_level
        return xp_for_next_level(obj.current_level)
        
    def get_level_progress(self, obj):
        from activities.logic.xp_service import xp_for_level, xp_for_next_level
        start = xp_for_level(obj.current_level)
        end = xp_for_next_level(obj.current_level)
        if end == start:
            return 1.0
        return min(1.0, max(0.0, (obj.total_xp - start) / float(end - start)))


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    display_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            display_name=validated_data.get('display_name', '') or validated_data['username'],
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        username_or_email = attrs.get('username')
        password = attrs.get('password')

        user = None
        # Support login via either username or email
        if '@' in username_or_email:
            matching_user = User.objects.filter(email__iexact=username_or_email).first()
            if matching_user:
                user = authenticate(
                    request=self.context.get('request'),
                    username=matching_user.username,
                    password=password,
                )
        if not user:
            user = authenticate(
                request=self.context.get('request'),
                username=username_or_email,
                password=password,
            )

        if not user:
            raise serializers.ValidationError({"detail": "Invalid username or password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        attrs['user'] = user
        return attrs


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['display_name', 'email', 'location_privacy_mode']
