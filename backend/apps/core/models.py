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
    topic = models.CharField(
        max_length=100,
        blank=True,
        help_text="Syllabus topic, e.g. 'Kinematics' — powers weak-topic practice.",
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
    answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-question detail: {question_id: {selected, correct, topic}} "
        "— the raw material for weak-topic analytics.",
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.enrollment.student.email} - {self.quiz.title} - {self.score}%"


class ShortAnswerQuestion(models.Model):
    """A free-text question graded by the ml-service against an official
    mark scheme — instant rubric feedback for open-ended answers."""

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="short_answer_questions"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="short_answer_questions",
    )
    prompt = models.TextField()
    mark_scheme = models.TextField(
        help_text="Official rubric the grader scores against. One criterion "
        "per line. Never exposed to students through the API."
    )
    topic = models.CharField(
        max_length=100,
        blank=True,
        help_text="Syllabus topic, e.g. 'Kinematics' — powers weak-topic practice.",
    )
    max_score = models.PositiveIntegerField(default=5)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Short answer {self.id} for {self.course.title}"


class ShortAnswerSubmission(models.Model):
    """A student's graded free-text answer, with the criteria breakdown the
    grader returned."""

    class Engine(models.TextChoices):
        LLM = "llm", "Fine-tuned LLM"
        HEURISTIC = "heuristic", "Criterion overlap"

    question = models.ForeignKey(
        ShortAnswerQuestion, on_delete=models.CASCADE, related_name="submissions"
    )
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="short_answer_submissions"
    )
    answer_text = models.TextField()
    score = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField()
    criteria_met = models.JSONField(default=list, blank=True)
    criteria_missing = models.JSONField(default=list, blank=True)
    feedback = models.TextField(blank=True)
    engine = models.CharField(
        max_length=20, choices=Engine.choices, default=Engine.HEURISTIC
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["question", "enrollment"])]

    def __str__(self):
        return (
            f"{self.enrollment.student.email} - Q{self.question_id} - "
            f"{self.score}/{self.max_score}"
        )


class ProctoringLog(models.Model):
    """One webcam-frame proctoring verdict during a quiz attempt — the raw
    material for the instructor's exam-integrity timeline. No images are
    stored, only the face-count verdict."""

    class Verdict(models.TextChoices):
        OK = "ok", "OK"
        NO_FACE = "no_face", "No face"
        MULTIPLE_FACES = "multiple_faces", "Multiple faces"

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="proctoring_logs"
    )
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="proctoring_logs"
    )
    faces = models.PositiveIntegerField()
    verdict = models.CharField(max_length=20, choices=Verdict.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["quiz", "enrollment", "created_at"])]

    @property
    def is_violation(self):
        return self.verdict != self.Verdict.OK

    def __str__(self):
        return f"{self.enrollment.student.email} - {self.quiz.title} - {self.verdict}"
