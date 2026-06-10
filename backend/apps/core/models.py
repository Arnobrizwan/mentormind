from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Course(models.Model):
    """A learning program created by an instructor."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    instructor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="taught_courses"
    )
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Lesson(models.Model):
    """An individual unit of study within a Course."""

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=255)
    content = models.TextField(help_text="Markdown or text content of the lesson.")
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(
        default=0, help_text="Order in which this lesson appears in the course."
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Quiz(models.Model):
    """A quiz assessment linked to a course or optionally specific lesson."""

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="quizzes"
    )
    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="quiz",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    """A question belonging to a Quiz."""

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField()
    options = models.JSONField(
        help_text="A JSON array/list of string options, e.g. ['A', 'B', 'C']"
    )
    correct_option_index = models.PositiveIntegerField(
        help_text="Zero-based index of the correct option in the options array."
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Question {self.id} for {self.quiz.title}"


class Enrollment(models.Model):
    """A student's enrollment status and learning progress in a Course."""

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_lessons = models.ManyToManyField(
        Lesson, blank=True, related_name="completed_by"
    )

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.email} enrolled in {self.course.title}"


class QuizAttempt(models.Model):
    """A record of a student's attempt and score on a Quiz."""

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="attempts"
    )
    score = models.FloatField(help_text="Percentage score (0-100).")
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.enrollment.student.email} - {self.quiz.title} - {self.score}%"
