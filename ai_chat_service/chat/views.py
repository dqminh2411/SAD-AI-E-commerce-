from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import ChatbotService, ensure_kb_index


class ChatHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class ChatMessageView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        user_id = request.data.get('user_id', '').strip()
        message = request.data.get('message', '').strip()
        context = request.data.get('context', {})

        if not user_id or not message:
            return Response(
                {'detail': 'user_id and message are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ensure_kb_index()
        service = ChatbotService()
        try:
            data = service.answer(user_id=user_id, message=message, context=context)
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            # Always return JSON so api_gateway never fails parsing upstream response.
            return Response(
                {'detail': 'ai_chat_service internal error'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
