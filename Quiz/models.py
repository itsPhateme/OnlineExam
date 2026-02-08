import random

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


class TeacherManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(user_type='teacher')


class StudentManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(user_type='student')


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)

    objects = UserManager()
    teachers = TeacherManager()
    students = StudentManager()

    def __str__(self):
        return f"{self.username} ({self.user_type})"


class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Exam(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'teacher'})
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    total_score = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject.name}"

    @property
    def end_time(self):
        return self.start_date + timezone.timedelta(minutes=self.duration_minutes)


class Question(models.Model):
    QUESTION_TYPES = (
        ('short', 'Short Answer'),
        ('long', 'Long Answer'),
        ('mcq', 'Multiple Choice'),
        ('file', 'File Upload'),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    text = models.TextField()
    marks = models.PositiveIntegerField(default=1)
    model_answer = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Q{self.id} ({self.question_type}) - {self.exam.title}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Choice for Q{self.question.id}"


class StudentExam(models.Model):
    student = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0)
    is_finished = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"

    def time_remaining(self):
        if self.started_at:
            elapsed = timezone.now() - self.started_at
            total = timezone.timedelta(minutes=self.exam.duration_minutes)
            remaining = total - elapsed
            return max(remaining, timezone.timedelta(seconds=0))
        return timezone.timedelta(minutes=self.exam.duration_minutes)

    def mark_as_finished(self):
        self.is_finished = True
        self.finished_at = timezone.now()
        self.save()

    @property
    def needs_grading(self):
        return self.answers.filter(
            question__question_type__in=['short', 'long', 'file'],
            evaluated=False
        ).exists()

    def calculate_final_score(self):
        auto_score = self.answers.filter(
            question__question_type='mcq',
            evaluated=True
        ).aggregate(total=models.Sum('marks_obtained'))['total'] or 0

        manual_score = self.answers.filter(
            question__question_type__in=['short', 'long', 'file'],
            evaluated=True
        ).aggregate(total=models.Sum('marks_obtained'))['total'] or 0

        self.score = auto_score + manual_score
        self.save(update_fields=['score'])

    def auto_grade_mcq_answers(self):
        mcq_answers = self.answers.filter(question__question_type='mcq', evaluated=False)
        for answer in mcq_answers:
            answer.auto_grade()


class Answer(models.Model):
    student_exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True, null=True)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, blank=True, null=True)
    uploaded_file = models.FileField(upload_to='answers/files/', blank=True, null=True)
    marks_obtained = models.FloatField(default=0, blank=True)
    evaluated = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer by {self.student_exam.student.username} - Q{self.question.id}"

    def auto_grade(self):
        if self.question.question_type == 'mcq':
            if self.selected_choice and self.selected_choice.is_correct:
                self.marks_obtained = self.question.marks
        elif self.question.question_type in ['short', 'long']:
            if self.question.model_answer:
                if self.question.model_answer.lower().strip() in (self.answer_text or "").lower():
                    self.marks_obtained = self.question.marks
        self.evaluated = True
        self.save()


class OTP(models.Model):
    phone = models.CharField(max_length=15)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_code(self):
        self.code = str(random.randint(100000, 999999))
        self.save()

    def is_valid(self):
        return timezone.now() < self.created_at + timezone.timedelta(minutes=2)

    def __str__(self):
        return f"{self.phone} - {self.code}"
