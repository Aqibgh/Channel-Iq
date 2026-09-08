"""Authentication API handlers."""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import CustomUser

logger = logging.getLogger(__name__)

try:
    from firebase_admin import auth as firebase_auth
except ImportError:
    firebase_auth = None


@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    token = request.data.get('token')
    user_id = request.data.get('userId')

    if not token:
        return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

    if not settings.FIREBASE_ENABLED:
        return Response({'error': 'Firebase authentication is not configured'}, status=503)

    try:
        # Step 1: Decode Firebase token
        decoded_token = firebase_auth.verify_id_token(token)
        email = decoded_token.get('email')
        name = decoded_token.get('name', '')
        firebase_uid = decoded_token.get('uid') or user_id

        if not email:
            return Response({'error': 'Email not found in token'}, status=status.HTTP_401_UNAUTHORIZED)

        # Step 2: Find or create user
        user = CustomUser.objects.filter(email__iexact=email).first()
        if not user:
            user = CustomUser.objects.create_user(
                email=email,
                username=email,  # Or use firebase_uid as username
                first_name=name.split(' ')[0] if name else '',
                last_name=name.split(' ')[1] if name and ' ' in name else '',
                firebase_uid=firebase_uid,
                is_active=True,
            )
            created = True
        else:
            if not user.firebase_uid:
                user.firebase_uid = firebase_uid
                user.save()
            created = False

        # Step 3: Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'name': name,
                'firebase_uid': firebase_uid,
                'is_new': created
            }
        })

    except Exception as e:
        logger.error(f"Error in google_login: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Authentication failed', 'debug': str(e) if settings.DEBUG else None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
