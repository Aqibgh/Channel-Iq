from django.urls import path
from . import views
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
import logging
from django.utils import timezone
logger = logging.getLogger(__name__)
@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Simple health check endpoint for load balancer/monitoring
    """
    try:
        # Basic health checks
        from django.db import connection
        from django.core.cache import cache
        
        health_status = {
            "status": "healthy",
            "timestamp": str(timezone.now()),
            "checks": {}
        }
        
        # Database check (optional - remove if using SQLite and experiencing issues)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["checks"]["database"] = "ok"
        except Exception as e:
            health_status["checks"]["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"
        
        # Cache check (optional)
        try:
            cache.set("health_check", "ok", 30)
            cache_value = cache.get("health_check")
            if cache_value == "ok":
                health_status["checks"]["cache"] = "ok"
            else:
                health_status["checks"]["cache"] = "error: cache test failed"
        except Exception as e:
            health_status["checks"]["cache"] = f"error: {str(e)}"
        
        # Memory check
        import psutil
        memory = psutil.virtual_memory()
        health_status["checks"]["memory_usage"] = f"{memory.percent}%"
        
        if memory.percent > 90:
            health_status["status"] = "warning"
        
        status_code = 200 if health_status["status"] in ["healthy", "warning"] else 503
        
        return JsonResponse(health_status, status=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "timestamp": str(timezone.now())
        }, status=503)
urlpatterns = [
    path('fetch-video/', views.fetch_video_data, name='fetch_video'),  # Fetch video metadata
    path('download-video/', views.download_video, name='download_video'),  # Download video
    path('process_short_form_video/', views.process_short_form_video, name='process_video'),  # Process short-form video
    path('seo/', views.seo, name='seo'),  # SEO endpoint
    path('optimize_shortform/', views.optimize_shortform, name='optimize_shortform'),
    path('check-resolution/', views.check_resolution, name='check-resolution'),  # Check resolution endpoint
    path('fetch-data/', views.fetch_data, name='fetch_data'),
    path('videos/<str:video_id>/', views.get_video, name='get_video'),
    path('youtube/check-auth/', views.check_auth, name='youtube-check-auth'),
    path('youtube/authorize/', views.authorize_youtube, name='youtube-authorize'),
    path('youtube/callback/', views.youtube_callback, name='youtube-callback'),
    path('youtube/upload/', views.upload_youtube_video, name='youtube-upload'),
    path('auth/google-login/', views.google_login, name='google-login'),
    path('youtube/get-auth-url/', views.get_youtube_auth_url, name='youtube_auth_url'),
    path('youtube/update-seo/', views.update_youtube_seo, name='update_youtube_seo'),
    path('generate-report/', views.generate_report, name='generate_report'),  # New endpoint for report generation
]
