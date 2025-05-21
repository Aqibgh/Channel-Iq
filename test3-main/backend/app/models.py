from django.db import models
from django.conf import settings
import google.oauth2.credentials
import googleapiclient.discovery
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
# Create your models here.
class React(models.Model):
    employee=models.CharField(max_length=30)
    department=models.CharField(max_length=200)

class ClipGenerationTask(models.Model):
    video_url = models.URLField()
    clip_length = models.IntegerField()
    clip_count = models.IntegerField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
class YouTubeAuth(models.Model):
    """Model to store YouTube OAuth credentials"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    credentials = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_valid(self):
        """Check if credentials are valid"""
        if not self.credentials:
            return False
            
        # Check if we have the necessary credentials
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
        for field in required_fields:
            if field not in self.credentials:
                return False
        
        try:
            # Create credentials object
            credentials = google.oauth2.credentials.Credentials(
                token=self.credentials.get('token'),
                refresh_token=self.credentials.get('refresh_token'),
                token_uri=self.credentials.get('token_uri'),
                client_id=self.credentials.get('client_id'),
                client_secret=self.credentials.get('client_secret'),
                scopes=self.credentials.get('scopes')
            )
            
            # Try to build YouTube service
            youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
            
            # Make a simple API call to test credentials
            response = youtube.channels().list(part='snippet', mine=True).execute()
            
            # Update token if it was refreshed
            if credentials.token != self.credentials.get('token'):
                self.credentials['token'] = credentials.token
                self.save()
                
            return True
            
        except Exception:
            return False
class CustomUser(AbstractUser):
    """
    Custom User model that extends Django's AbstractUser to include
    Firebase authentication fields and additional user information.
    """
    # Fix the related_name conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='customuser_set',  # Changed from default 'user_set'
        related_query_name='user',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='customuser_set',  # Changed from default 'user_set'
        related_query_name='user',
    )
    
    # Firebase and other custom fields
    firebase_uid = models.CharField(
        _('Firebase UID'),
        max_length=128,
        blank=True,
        null=True,
        unique=True,
        help_text=_('Unique identifier from Firebase authentication')
    )
    
    profile_picture = models.URLField(
        _('Profile Picture URL'),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_('URL to the user\'s profile picture from Google/Firebase')
    )
    
    last_login_firebase = models.DateTimeField(
        _('Last Firebase Login'),
        blank=True,
        null=True,
        default=None,
        help_text=_('The last time the user logged in via Firebase')
    )
    
    is_verified_email = models.BooleanField(
        _('Email Verified'),
        default=False,
        help_text=_('Whether the user\'s email has been verified')
    )
    
    # Additional metadata that could be useful
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        
    def __str__(self):
        return self.email or self.username
    
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        If either is empty, return just the non-empty value.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.username