from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from .models import Course, Enrollment, Lesson, Quiz, QuizAttempt, QuizQuestion


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "course",
            "title",
            "content",
            "video_url",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get("request")
        if request:
            user = request.user
            # Check if enrolled
            is_enrolled = (
                user.is_authenticated
                and (
                    user.is_staff
                    or user.is_superuser
                    or instance.course.instructor == user
                    or Enrollment.objects.filter(
                        student=user, course=instance.course
                    ).exists()
                )
            )
            if not is_enrolled:
                rep["content"] = "Enroll in this course to unlock this lesson's content."
                rep["video_url"] = None
        else:
            rep["content"] = "Enroll in this course to unlock this lesson's content."
            rep["video_url"] = None
        return rep


class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = ("id", "quiz", "text", "options", "correct_option_index", "order")
        read_only_fields = ("id",)

    def validate(self, data):
        options = data.get("options", self.instance.options if self.instance else None)
        index = data.get(
            "correct_option_index",
            self.instance.correct_option_index if self.instance else None,
        )
        if not isinstance(options, list) or len(options) < 2:
            raise serializers.ValidationError(
                {"options": "Provide a list of at least 2 options."}
            )
        if not all(isinstance(o, str) and o.strip() for o in options):
            raise serializers.ValidationError(
                {"options": "Every option must be a non-empty string."}
            )
        if index is not None and index >= len(options):
            raise serializers.ValidationError(
                {"correct_option_index": "Index is out of range for the options list."}
            )
        return data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get("request")
        if request and request.user:
            user = request.user
            course = instance.quiz.course
            # If user is not instructor of the course and not staff/superuser, hide the solution index
            if not (user.is_staff or user.is_superuser or course.instructor == user):
                rep.pop("correct_option_index", None)
        else:
            rep.pop("correct_option_index", None)
        return rep


class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "course",
            "lesson",
            "title",
            "description",
            "questions",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CourseSerializer(serializers.ModelSerializer):
    instructor_name = serializers.ReadOnlyField(source="instructor.display_name")
    lessons = LessonSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "instructor",
            "instructor_name",
            "cover_image",
            "is_published",
            "lessons",
            "quizzes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "instructor", "created_at", "updated_at")


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.ReadOnlyField(source="quiz.title")

    class Meta:
        model = QuizAttempt
        fields = (
            "id",
            "enrollment",
            "quiz",
            "quiz_title",
            "score",
            "total_questions",
            "correct_answers",
            "completed_at",
        )
        read_only_fields = ("id", "completed_at")


class EnrollmentSerializer(serializers.ModelSerializer):
    student_email = serializers.ReadOnlyField(source="student.email")
    student_name = serializers.ReadOnlyField(source="student.display_name")
    course_title = serializers.ReadOnlyField(source="course.title")
    progress_percentage = serializers.SerializerMethodField()
    quiz_attempts = QuizAttemptSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "student",
            "student_email",
            "student_name",
            "course",
            "course_title",
            "enrolled_at",
            "completed_lessons",
            "progress_percentage",
            "quiz_attempts",
        )
        read_only_fields = ("id", "student", "enrolled_at", "completed_lessons")

    def get_progress_percentage(self, instance):
        # Read from default alias to ensure it is strongly consistent after a write
        total_lessons = Lesson.objects.using("default").filter(course=instance.course, is_published=True).count()
        if total_lessons == 0:
            return 0.0
        completed = instance.completed_lessons.using("default").count()
        return round((completed / total_lessons) * 100, 2)
