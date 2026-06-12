"""Student-facing proxy to the ml-service past-paper corpus — browse,
reveal, and sample real Cambridge questions. The corpus lives with the
ml-service; these views only forward with the shared API key."""

from urllib.parse import urlencode

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ml_client


def _proxy(path):
    try:
        return Response(ml_client.get_json(path, timeout=20))
    except ml_client.MLServiceError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class PaperSubjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return _proxy("/v1/papers/subjects")


class PaperQuestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = {}
        if request.query_params.get("subject_code"):
            params["subject_code"] = request.query_params["subject_code"][:8]
        for key, cap in (("page", 100000), ("page_size", 50)):
            raw = request.query_params.get(key)
            if raw is not None:
                try:
                    params[key] = max(1, min(int(raw), cap))
                except ValueError:
                    return Response(
                        {"error": f"{key} must be an integer."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        return _proxy("/v1/papers/questions" + ("?" + urlencode(params) if params else ""))


class PaperQuestionDetailView(APIView):
    """The reveal — includes the official mark scheme."""

    permission_classes = [IsAuthenticated]

    def get(self, request, question_id):
        return _proxy(f"/v1/papers/questions/{question_id}")


class PaperSampleView(APIView):
    """Random question set for mock exams (mark schemes included — used
    client-side for self-marking after the timer ends)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = {}
        if request.query_params.get("subject_code"):
            params["subject_code"] = request.query_params["subject_code"][:8]
        try:
            params["count"] = max(1, min(int(request.query_params.get("count", 10)), 20))
        except ValueError:
            return Response({"error": "count must be an integer."}, status=400)
        return _proxy("/v1/papers/sample?" + urlencode(params))
