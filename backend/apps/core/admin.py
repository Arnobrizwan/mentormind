from django.contrib import admin

from .models import Course, Enrollment, Lesson, Quiz, QuizAttempt, QuizQuestion


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("title", "order", "is_published")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "instructor", "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "is_published", "updated_at")
    list_filter = ("is_published", "course")
    search_fields = ("title", "content")


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "lesson", "updated_at")
    list_filter = ("course",)
    search_fields = ("title", "description")
    inlines = [QuizQuestionInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "enrolled_at")
    list_filter = ("course",)
    search_fields = ("student__email", "course__title")
    autocomplete_fields = ("student", "course")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "quiz", "score", "completed_at")
    list_filter = ("quiz",)
    readonly_fields = ("completed_at",)


from .models import ProctoringLog, ShortAnswerQuestion, ShortAnswerSubmission  # noqa: E402


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "text", "topic", "order")
    list_filter = ("quiz__course", "topic")
    search_fields = ("text", "topic")


@admin.register(ShortAnswerQuestion)
class ShortAnswerQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "topic", "prompt", "max_score", "is_published")
    list_filter = ("is_published", "course", "topic")
    search_fields = ("prompt", "mark_scheme", "topic")


@admin.register(ShortAnswerSubmission)
class ShortAnswerSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "enrollment", "score", "max_score", "engine", "created_at")
    list_filter = ("engine", "question__course")
    search_fields = ("enrollment__student__email", "answer_text")
    readonly_fields = ("created_at",)


@admin.register(ProctoringLog)
class ProctoringLogAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "enrollment", "verdict", "faces", "created_at")
    list_filter = ("verdict", "quiz")
    search_fields = ("enrollment__student__email",)
    readonly_fields = ("created_at",)
