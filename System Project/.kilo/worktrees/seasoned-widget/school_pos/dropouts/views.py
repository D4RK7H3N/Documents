from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from students.models import Student
from .models import Dropout
from .serializers import DropoutSerializer


class DropoutViewSet(viewsets.ModelViewSet):
    """Dropout student management"""

    queryset = Dropout.objects.all()
    serializer_class = DropoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Confirmed dropouts by default, with the existing filters applied.

        Reinstatement flags the record 'reinstated' instead of deleting it so
        the history survives. Those rows are history, not current dropouts, so
        they stay out of the default list; pass ?all=true to include them.

        This used to be two separate get_queryset methods - a later one
        silently overrode the status filter, so reinstated students kept
        showing on the dropouts list.
        """
        queryset = Dropout.objects.select_related('student').all()

        if self.request.query_params.get('all', 'false').lower() != 'true':
            queryset = queryset.filter(status='confirmed')

        search = self.request.query_params.get('search', '')
        level_type = self.request.query_params.get('level_type', '')
        reason = self.request.query_params.get('reason', '')

        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search)
                | Q(student__last_name__icontains=search)
                | Q(student__lrn__icontains=search)
                | Q(reason__icontains=search)
            )

        if level_type:
            queryset = queryset.filter(student__level_type=level_type)

        if reason:
            queryset = queryset.filter(reason__icontains=reason)

        return queryset.order_by('-dropout_date')

    @action(detail=False, methods=['get'])
    def all_dropouts(self, request):
        """Get all students currently marked as Drop-out (not necessarily in Dropout table)"""
        status_filter = request.query_params.get('status', 'Drop-out')
        students = Student.objects.filter(status=status_filter).order_by('-id')
        serializer = DropoutSerializer(
            [Dropout(student=s, dropout_date=timezone.now().date()) for s in students],
            many=True
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reinstate(self, request, pk=None):
        """Reinstate a dropout student to Active status.

        The record is flagged rather than deleted so the dropout history
        survives and a reinstated student stops blocking promotion.
        """
        dropout = self.get_object()
        student = dropout.student

        student.status = 'Active'
        student.save()

        dropout.status = 'reinstated'
        dropout.reinstated_at = timezone.now()
        dropout.save(update_fields=['status', 'reinstated_at', 'updated_at'])

        return Response({
            'success': True,
            'message': f'Student {student.lrn} ({student.first_name} {student.last_name}) reinstated successfully.',
            'student_id': student.id,
            'new_status': student.status,
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get dropout statistics"""
        total_dropouts = Dropout.objects.count()
        by_level = {}
        for level in ['SHS', 'COL', 'BUN']:
            count = Dropout.objects.filter(student__level_type=level).count()
            by_level[level] = count

        return Response({
            'total_dropouts': total_dropouts,
            'by_level_type': by_level,
        })