from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Track, Strand, Course, Section
from .serializers import (
    TrackSerializer,
    TrackListSerializer,
    StrandSerializer,
    StrandListSerializer,
    StrandCreateSerializer,
    TrackStrandAutoCreateSerializer,
    CourseSerializer,
    CourseListSerializer,
    SectionSerializer,
    SectionListSerializer,
)


class TrackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing academic tracks.

    Endpoints:
    - GET /api/tracks/ - List all tracks
    - POST /api/tracks/ - Create a new track
    - GET /api/tracks/{id}/ - Get track details
    - PUT /api/tracks/{id}/ - Update track
    - DELETE /api/tracks/{id}/ - Delete track
    - GET /api/tracks/active/ - List active tracks only
    - GET /api/tracks/by_level/?level=SHS - Filter by level type
    """

    queryset = Track.objects.all()
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return TrackListSerializer
        return TrackSerializer

    def get_queryset(self):
        queryset = Track.objects.all()

        # Filter by level type
        level_type = self.request.query_params.get("level", None)
        if level_type:
            queryset = queryset.filter(Q(level_type=level_type) | Q(level_type="ALL"))

        # Filter by active status
        is_active = self.request.query_params.get("active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("name")

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active tracks"""
        tracks = Track.objects.filter(is_active=True).order_by("name")
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_level(self, request):
        """Get tracks by level type"""
        level = request.query_params.get("level", "SHS")
        tracks = Track.objects.filter(
            Q(level_type=level) | Q(level_type="ALL"), is_active=True
        ).order_by("name")
        serializer = TrackListSerializer(tracks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def strands(self, request, pk=None):
        """Get all strands for a specific track"""
        track = self.get_object()
        strands = track.strands.filter(is_active=True)
        serializer = StrandListSerializer(strands, many=True)
        return Response(serializer.data)


class StrandViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing academic strands.

    Endpoints:
    - GET /api/strands/ - List all strands
    - POST /api/strands/ - Create a new strand
    - GET /api/strands/{id}/ - Get strand details
    - PUT /api/strands/{id}/ - Update strand
    - DELETE /api/strands/{id}/ - Delete strand
    - GET /api/strands/active/ - List active strands only
    - GET /api/strands/by_track/?track_id=1 - Filter by track
    - POST /api/strands/auto_create/ - Auto-create track and strand from name
    - GET /api/strands/search/?q=STEM - Search strands
    """

    queryset = Strand.objects.all()
    serializer_class = StrandSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return StrandListSerializer
        if self.action == "create":
            return StrandCreateSerializer
        if self.action == "auto_create":
            return TrackStrandAutoCreateSerializer
        return StrandSerializer

    def get_queryset(self):
        queryset = Strand.objects.select_related("track").all()

        # Filter by track
        track_id = self.request.query_params.get("track_id", None)
        if track_id:
            queryset = queryset.filter(track_id=track_id)

        # Filter by level type
        level_type = self.request.query_params.get("level", None)
        if level_type:
            queryset = queryset.filter(
                Q(track__level_type=level_type) | Q(track__level_type="ALL")
            )

        # Filter by active status
        is_active = self.request.query_params.get("active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("track__name", "name")

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active strands"""
        strands = (
            Strand.objects.select_related("track")
            .filter(is_active=True, track__is_active=True)
            .order_by("track__name", "name")
        )
        serializer = StrandListSerializer(strands, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_track(self, request):
        """Get strands by track ID"""
        track_id = request.query_params.get("track_id", None)
        if not track_id:
            return Response(
                {"error": "track_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        strands = Strand.objects.filter(track_id=track_id, is_active=True).order_by(
            "name"
        )
        serializer = StrandListSerializer(strands, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_level(self, request):
        """Get strands by level type"""
        level = request.query_params.get("level", "SHS")
        strands = (
            Strand.objects.select_related("track")
            .filter(
                Q(track__level_type=level) | Q(track__level_type="ALL"),
                is_active=True,
                track__is_active=True,
            )
            .order_by("track__name", "name")
        )
        serializer = StrandListSerializer(strands, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def auto_create(self, request):
        """
        Auto-create track and strand from a name string.

        Supports formats:
        - "STEM" - Creates strand with auto-generated track
        - "Academic Track - STEM" - Creates track "Academic Track" and strand "STEM"

        Request body:
        {
            "name": "STEM" or "Academic Track - STEM",
            "level_type": "SHS" (optional, defaults to SHS)
        }
        """
        serializer = TrackStrandAutoCreateSerializer(data=request.data)
        if serializer.is_valid():
            strand = serializer.save()
            return Response(
                StrandSerializer(strand).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search strands by name or code"""
        query = request.query_params.get("q", "")
        if len(query) < 1:
            return Response([])

        strands = (
            Strand.objects.select_related("track")
            .filter(
                Q(name__icontains=query)
                | Q(code__icontains=query)
                | Q(track__name__icontains=query),
                is_active=True,
                track__is_active=True,
            )
            .order_by("name")[:20]
        )

        serializer = StrandListSerializer(strands, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def all_options(self, request):
        """
        Get all track/strand options formatted for dropdown selection.
        Returns a flat list of all strands with their track info.
        """
        level = request.query_params.get("level", None)

        queryset = Strand.objects.select_related("track").filter(
            is_active=True, track__is_active=True
        )

        if level:
            queryset = queryset.filter(
                Q(track__level_type=level) | Q(track__level_type="ALL")
            )

        strands = queryset.order_by("track__name", "name")

        options = []
        for strand in strands:
            options.append(
                {
                    "id": strand.id,
                    "value": strand.code,
                    "label": f"{strand.name} ({strand.code})",
                    "track_id": strand.track.id,
                    "track_name": strand.track.name,
                    "full_label": f"{strand.track.name} - {strand.name}",
                }
            )

        return Response(options)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing courses (College and Bundled programs).

    Endpoints:
    - GET /api/courses/ - List all courses
    - POST /api/courses/ - Create a new course
    - GET /api/courses/{id}/ - Get course details
    - PUT /api/courses/{id}/ - Update course
    - DELETE /api/courses/{id}/ - Delete course
    - GET /api/courses/active/ - List active courses only
    - GET /api/courses/by_level/?level=COL - Filter by level type
    - GET /api/courses/search/?q=query - Search courses
    - GET /api/courses/all_options/ - Get all options for dropdowns
    """

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        return CourseSerializer

    def get_queryset(self):
        queryset = Course.objects.all()

        # Filter by level type
        level_type = self.request.query_params.get("level", None)
        if level_type:
            queryset = queryset.filter(level_type=level_type)

        # Filter by active status
        is_active = self.request.query_params.get("active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("name")

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active courses"""
        courses = Course.objects.filter(is_active=True).order_by("name")
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_level(self, request):
        """Get courses by level type (COL or BUN)"""
        level = request.query_params.get("level", "COL")
        courses = Course.objects.filter(level_type=level, is_active=True).order_by(
            "name"
        )
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """Search courses by name, code, or abbreviation"""
        query = request.query_params.get("q", "")
        if len(query) < 1:
            return Response([])

        courses = Course.objects.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(abbreviation__icontains=query),
            is_active=True,
        ).order_by("name")[:20]

        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def all_options(self, request):
        """
        Get all course options formatted for dropdown selection.
        """
        level = request.query_params.get("level", None)

        queryset = Course.objects.filter(is_active=True)

        if level:
            queryset = queryset.filter(level_type=level)

        courses = queryset.order_by("name")

        options = []
        for course in courses:
            options.append(
                {
                    "id": course.id,
                    "value": course.code,
                    "label": f"{course.name} ({course.code})",
                    "abbreviation": course.abbreviation,
                    "level_type": course.level_type,
                    "duration_years": course.duration_years,
                }
            )

        return Response(options)


# ============== SECTION VIEWS ==============


class SectionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing sections."""

    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return SectionListSerializer
        return SectionSerializer

    def get_queryset(self):
        queryset = Section.objects.all()
        level_type = self.request.query_params.get("level", None)
        if level_type:
            queryset = queryset.filter(level_type=level_type)
        grade_year = self.request.query_params.get("grade_year", None)
        if grade_year:
            queryset = queryset.filter(grade_year=grade_year)
        is_active = self.request.query_params.get("active", None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        return queryset.order_by("level_type", "grade_year", "name")

    @action(detail=False, methods=["get"])
    def active(self, request):
        sections = Section.objects.filter(is_active=True).order_by(
            "level_type", "grade_year", "name"
        )
        serializer = SectionListSerializer(sections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_level(self, request):
        level = request.query_params.get("level", "SHS")
        sections = Section.objects.filter(level_type=level, is_active=True).order_by(
            "grade_year", "name"
        )
        serializer = SectionListSerializer(sections, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def all_options(self, request):
        level = request.query_params.get("level", None)
        queryset = Section.objects.filter(is_active=True)
        if level:
            queryset = queryset.filter(level_type=level)
        sections = queryset.order_by("level_type", "grade_year", "name")
        options = [
            {
                "id": s.id,
                "value": s.name,
                "label": s.name,
                "level_type": s.level_type,
                "grade_year": s.grade_year,
            }
            for s in sections
        ]
        return Response(options)
