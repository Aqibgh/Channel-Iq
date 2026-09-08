"""Video analysis report API handler."""

import json
import logging

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report(request):
    """
    Generate a detailed video analysis report using report.py
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)

    try:
        # Parse the JSON body
        data = json.loads(request.body)
        video_url = data.get("videoURL")
        user_id = data.get("userId")
        user_email = data.get("userEmail")

        # Get OpenAI API key from settings
        openai_api_key = settings.OPENAI_API_KEY

        # Validate input
        if not video_url:
            return JsonResponse({"error": "Missing required parameter: videoURL"}, status=400)

        if not openai_api_key:
            return JsonResponse({"error": "OpenAI API key not configured"}, status=500)

        # Import the analyze_video function from report.py
        from .utils.report import analyze_video

        # Process the video and generate the report
        logger.info(f"Generating report for video: {video_url}")
        result = analyze_video(video_url, youtube_credentials=None, openai_api_key=openai_api_key)

        if result['status'] != 'success':
            return JsonResponse({"error": result['message']}, status=500)

        # Save report to Firestore if user is authenticated
        if user_id and user_email:
            # You may add Firestore saving logic here if needed
            pass

        # Return the analysis results
        return JsonResponse({
            "status": "success",
            "report": {
                "transcript_preview": result.get('transcript', ''),
                "full_analysis": result.get('full_analysis', ''),
                "key_suggestions": result.get('key_suggestions', [])
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data in request body"}, status=400)
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return JsonResponse({"error": str(e)}, status=500)
