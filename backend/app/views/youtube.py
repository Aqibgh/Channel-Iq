"""YouTube authorization, upload, and metadata API handlers."""

import os
import time
import httplib2

import google.auth.exceptions
import google.oauth2.credentials
import google_auth_httplib2
import google_auth_oauthlib.flow
import googleapiclient.discovery
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import YouTubeAuth
from .common import logger

User = get_user_model()

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_auth(request):
    if not request.user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=401)

    try:
        from .models import YouTubeAuth
        import google.oauth2.credentials
        import googleapiclient.discovery
        from google.auth.exceptions import RefreshError

        logger.debug("Checking YouTube auth for user %s", request.user.id)
        youtube_auth = YouTubeAuth.objects.filter(user=request.user).first()

        if not youtube_auth or not youtube_auth.credentials:
            logger.debug("No YouTube auth record or credentials found")
            return Response({'has_youtube_auth': False})

        # Try to actually use the credentials to verify they're valid
        try:
            creds_data = youtube_auth.credentials
            credentials = google.oauth2.credentials.Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )

            # Create a YouTube service object and make a simple request
            youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
            # Make a minimal request that requires authentication
            response = youtube.channels().list(part="snippet", mine=True).execute()

            logger.debug("YouTube credentials are valid")
            return Response({'has_youtube_auth': True})

        except RefreshError as e:
            # This happens when token is expired/revoked
            logger.info("YouTube token refresh failed: %s", e)
            return Response({'has_youtube_auth': False, 'reason': 'token_expired'})

        except Exception as e:
            logger.warning("Error validating YouTube credentials: %s", e)
            return Response({'has_youtube_auth': False, 'reason': 'validation_failed'})

    except Exception as e:
        logger.exception("Error checking YouTube auth")
        return Response({'has_youtube_auth': False, 'reason': 'server_error'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def authorize_youtube(request):
    """Initiate YouTube authorization flow"""
    if not os.path.isfile(settings.GOOGLE_CLIENT_SECRETS_FILE):
        return Response({'error': 'YouTube OAuth is not configured'}, status=503)

    # Create OAuth 2.0 flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES
    )

    # Set redirect URI
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')

    # Generate authorization URL and state
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force to always prompt for consent to get refresh token
    )

    # Store state in session
    request.session['youtube_auth_state'] = state
    request.session['user_id'] = request.user.id

    # Redirect to authorization URL
    return redirect(authorization_url)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@csrf_exempt
def youtube_callback(request):
    """Handle callback from YouTube authorization"""
    if not os.path.isfile(settings.GOOGLE_CLIENT_SECRETS_FILE):
        return JsonResponse({'error': 'YouTube OAuth is not configured'}, status=503)

    # Get state from request parameters (not from session)
    state = request.GET.get('state')

    if not state or ':' not in state:
        return JsonResponse({'error': 'Invalid state format'}, status=400)

    # Extract user ID from state
    try:
        user_id, state_uuid = state.split(':', 1)
        user_id = int(user_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid state content'}, status=400)

    # Get authorization code from request
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'No authorization code'}, status=400)

    # Create flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state  # Use the complete state from the request
    )
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')

    # Exchange authorization code for access token
    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
    except Exception as e:
        return JsonResponse({'error': f'Token exchange failed: {str(e)}'}, status=400)

    # Save credentials to database
    from .models import YouTubeAuth
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': f'User not found with ID: {user_id}'}, status=404)

    youtube_auth, created = YouTubeAuth.objects.get_or_create(user=user)
    youtube_auth.credentials = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    youtube_auth.save()

    # Return HTML response instead of redirecting
    html_response = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Authorization Successful</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
            .success { color: #28a745; }
        </style>
    </head>
    <body>
        <h2 class="success">YouTube Authorization Successful!</h2>
        <p>You can now close this window and return to Channel-IQ.</p>
        <script>
            // Close window automatically after 3 seconds
            setTimeout(function() {
                window.close();
            }, 3000);
        </script>
    </body>
    </html>
    """
    return HttpResponse(html_response)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_youtube_video(request):
    """Download video from S3 URL and upload to YouTube with improved token handling"""
    user = request.user

    # Check if user has valid YouTube credentials
    try:
        from .models import YouTubeAuth
        youtube_auth = YouTubeAuth.objects.get(user=user)
        if not youtube_auth.credentials:
            return Response({
                'error': 'YouTube authorization required',
                'needs_auth': True
            }, status=401)
    except YouTubeAuth.DoesNotExist:
        return Response({
            'error': 'YouTube authorization required',
            'needs_auth': True
        }, status=401)

    # Get video URL and metadata
    video_url = request.POST.get('video_url')
    s3_key = request.POST.get('s3_key', '')
    title = request.POST.get('title', 'My Video')
    description = request.POST.get('description', '')
    tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []

    if not video_url:
        return Response({'error': 'No video URL provided'}, status=400)

    # Initialize variables for resource cleanup
    temp_file_name = None
    media = None

    try:
        # Download video from URL
        import tempfile
        import os
        import requests

        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_file_name = temp_file.name
        temp_file.close()

        # Download the file from the URL
        if "amazonaws.com" in video_url and s3_key:
            # For S3 URLs, we can optionally use boto3 instead of requests
            response = requests.get(video_url, stream=True)
        else:
            # For local or other URLs
            response = requests.get(video_url, stream=True)

        response.raise_for_status()

        # Write the content to the temporary file
        with open(temp_file_name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.debug("Downloaded video to temporary file: %s", temp_file_name)
        logger.debug("Temporary file size: %s", os.path.getsize(temp_file_name))

        # Use Google OAuth credentials with improved token handling
        from google.oauth2 import credentials as google_credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.auth.exceptions import RefreshError

        # Get credentials from database
        creds_data = youtube_auth.credentials
        credentials = google_credentials.Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )

        # Validate token before proceeding
        try:
            # Force a token refresh to check validity
            auth_req = google_auth_httplib2.Request(httplib2.Http())
            credentials.refresh(auth_req)

            # Update credentials in database after refresh
            youtube_auth.credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            youtube_auth.save()

        # In upload_youtube_video view function
        except RefreshError as refresh_error:
            # Token is invalid and couldn't be refreshed
            if 'invalid_grant' in str(refresh_error):
                # Set to empty dict instead of None to satisfy NOT NULL constraint
                youtube_auth.credentials = {}  # Instead of None
                youtube_auth.save()

                return Response({
                    'error': 'YouTube authorization expired',
                    'needs_auth': True,
                    'detail': 'Your YouTube authorization has expired. Please re-authorize.'
                }, status=401)

        # Create YouTube service with validated credentials
        youtube = build('youtube', 'v3', credentials=credentials)

        # Create video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'  # People & Blogs category
            },
            'status': {
                'privacyStatus': 'private',  # Start as private, can be changed later
                'selfDeclaredMadeForKids': False
            }
        }

        # Upload video file
        media = MediaFileUpload(
            temp_file_name,
            mimetype='video/mp4',
            resumable=True
        )

        # Execute upload request with error handling
        try:
            request = youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )

            response = request.execute()
            logger.info("YouTube upload successful: %s", response.get('id'))

            # Return video ID
            return Response({'success': True, 'video_id': response['id']})

        except Exception as api_error:
            # Check if this is a token-related error
            error_str = str(api_error).lower()
            if 'invalid_grant' in error_str or 'unauthorized' in error_str or '401' in error_str:
                # Set to empty dict instead of None
                youtube_auth.credentials = {}  # Instead of None
                youtube_auth.save()

                return Response({
                    'error': 'YouTube authorization error during upload',
                    'needs_auth': True,
                    'detail': 'Your YouTube authorization has expired. Please re-authorize.'
                }, status=401)
            else:
                # Some other API error occurred
                raise

    except requests.RequestException as e:
        logger.error("Failed to download video: %s", e)
        return Response({'error': f'Failed to download video: {str(e)}'}, status=500)

    except Exception as e:
        logger.exception("YouTube upload failed")
        return Response({'error': str(e)}, status=500)

    finally:
    # Clean up resources
        if temp_file_name:
            if media:
                # Try to close the media
                try:
                    media.stream().close()
                except Exception:
                    pass

            # Add a small delay before trying to delete
            import time
            time.sleep(2)

            cleanup_temporary_file(temp_file_name, media)


def cleanup_temporary_file(temp_file_name, media=None):
    """Helper function to clean up temporary files with proper error handling"""
    if not temp_file_name:
        return

    import os
    import time
    import platform

    # Close the MediaFileUpload object to release the file
    if media:
        try:
            media.close()
        except Exception:
            pass

    # Wait longer before trying to delete the file on Windows
    if platform.system() == 'Windows':
        time.sleep(1.5)
    else:
        time.sleep(0.5)

    # Clean up temporary file with error handling and retry mechanism
    max_retries = 3  # Increased from 1 to 3 for better reliability
    retry_count = 0
    while retry_count < max_retries:
        try:
            if os.path.exists(temp_file_name):
                os.unlink(temp_file_name)
                logger.info("Deleted temporary file: %s", temp_file_name)
                break
        except Exception as e:
            retry_count += 1
            logger.warning(
                "Attempt %s - could not delete temporary file: %s",
                retry_count,
                e,
            )
            if retry_count < max_retries:
                time.sleep(2.0)  # Increased wait time between attempts
            else:
                logger.error(
                    "Failed to delete temporary file after %s attempts",
                    max_retries,
                )
                # On Windows, schedule the file for deletion on next reboot as a last resort
                if platform.system() == 'Windows':
                    try:
                        import ctypes
                        MOVEFILE_DELAY_UNTIL_REBOOT = 4
                        ctypes.windll.kernel32.MoveFileExW(temp_file_name, None, MOVEFILE_DELAY_UNTIL_REBOOT)
                        logger.info(
                            "File scheduled for deletion on next reboot: %s",
                            temp_file_name,
                        )
                    except Exception as move_ex:
                        logger.error("Failed to schedule file for deletion: %s", move_ex)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_youtube_auth_url(request):
    """Generate and return a YouTube authorization URL with user ID embedded in state"""
    if not os.path.isfile(settings.GOOGLE_CLIENT_SECRETS_FILE):
        return Response({'error': 'YouTube OAuth is not configured'}, status=503)

    # Create OAuth 2.0 flow instance
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES
    )

    # Set redirect URI
    flow.redirect_uri = request.build_absolute_uri('/api/youtube/callback/')

    # Create a state that includes the user ID
    import uuid
    state = f"{request.user.id}:{uuid.uuid4().hex}"

    # Generate authorization URL with our custom state
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state
    )

    # Return the authorization URL
    return Response({'auth_url': authorization_url})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_youtube_seo(request):
    """Update YouTube video SEO metadata"""
    user = request.user

    # Check if user has valid YouTube credentials
    try:
        from .models import YouTubeAuth
        youtube_auth = YouTubeAuth.objects.get(user=user)
        if not youtube_auth.credentials:
            return Response({'error': 'YouTube authorization required', 'needs_auth': True}, status=401)
    except YouTubeAuth.DoesNotExist:
        return Response({'error': 'YouTube authorization required', 'needs_auth': True}, status=401)

    # Get video ID and metadata
    video_id = request.POST.get('video_id')
    title = request.POST.get('title')
    description = request.POST.get('description')
    tags = request.POST.get('tags', '').split(',') if request.POST.get('tags') else []

    if not video_id:
        return Response({'error': 'No video ID provided'}, status=400)

    try:
        # Get credentials from database
        creds_data = youtube_auth.credentials
        credentials = google.oauth2.credentials.Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )

        # Create YouTube service
        youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)

        # First, get the current video details
        response = youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()

        if not response.get('items'):
            return Response({'error': 'Video not found or not accessible'}, status=404)

        # Check video ownership (verify the user owns this video)
        # Get the authenticated user's channel ID
        channels_response = youtube.channels().list(
            part="id",
            mine=True
        ).execute()

        if not channels_response.get('items'):
            return Response({'error': 'Could not retrieve your YouTube channel information'}, status=400)

        user_channel_id = channels_response['items'][0]['id']

        # Get the video's channel ID
        video_channel_id = response['items'][0]['snippet'].get('channelId')

        # Compare the channel IDs to verify ownership
        if user_channel_id != video_channel_id:
            return Response({
                'error': 'You can only update SEO for videos you own',
                'is_owner': False
            }, status=403)

        # Prepare snippet with updated information
        snippet = response['items'][0]['snippet']

        # Update only the provided fields
        if title:
            snippet['title'] = title
        if description:
            snippet['description'] = description
        if tags:
            snippet['tags'] = tags

        # Update video metadata
        update_response = youtube.videos().update(
            part='snippet',
            body={
                'id': video_id,
                'snippet': snippet
            }
        ).execute()

        # Update credentials if they were refreshed
        if credentials.token != creds_data.get('token'):
            youtube_auth.credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            youtube_auth.save()

        return Response({
            'success': True,
            'message': 'Video SEO updated successfully',
            'video_id': video_id
        })

    except google.auth.exceptions.RefreshError as e:
        # Handle token refresh errors (expired/revoked tokens)
        logger.info("YouTube token refresh failed: %s", e)

        # Mark the YouTube authentication as invalid
        youtube_auth.credentials = {}
        youtube_auth.save()

        return Response({
            'error': 'Your YouTube authorization has expired or been revoked',
            'needs_auth': True,
            'detail': str(e)
        }, status=401)

    except google.auth.exceptions.GoogleAuthError as e:
        # Handle other Google Auth errors
        logger.warning("YouTube authentication error: %s", e)

        return Response({
            'error': 'Authentication error with YouTube',
            'needs_auth': True,
            'detail': str(e)
        }, status=401)

    except Exception as e:
        logger.exception("YouTube SEO update failed")

        # Check if error is a 403 Forbidden (likely ownership issue)
        error_str = str(e).lower()
        if '403' in error_str and 'forbidden' in error_str:
            return Response({
                'error': 'You can only update SEO for videos you own',
                'is_owner': False
            }, status=403)

        # Check if the error message contains indicators of token problems
        elif ('token' in error_str and ('expired' in error_str or 'revoked' in error_str or 'invalid' in error_str)) or 'invalid_grant' in error_str:
            return Response({
                'error': 'Your YouTube authorization has expired or been revoked',
                'needs_auth': True,
                'detail': str(e)
            }, status=401)

        return Response({'error': str(e)}, status=500)
