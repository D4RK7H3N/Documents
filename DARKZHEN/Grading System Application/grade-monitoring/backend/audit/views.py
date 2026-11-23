from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import StandardPagination
from common.permissions import IsAdmin

from .models import AuditLog


class AuditLogView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AuditLog.objects.select_related("actor").all()
        params = request.query_params
        if params.get("entity"):
            qs = qs.filter(entity=params["entity"])
        if params.get("action"):
            qs = qs.filter(action=params["action"])
        if params.get("actor"):
            qs = qs.filter(actor__username__icontains=params["actor"])
        if params.get("since"):
            qs = qs.filter(timestamp__gte=params["since"])
        if params.get("until"):
            qs = qs.filter(timestamp__lte=params["until"])
        if params.get("q"):
            term = params["q"]
            qs = qs.filter(Q(new_values__icontains=term) | Q(old_values__icontains=term))
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([e.as_dict() for e in page])
