from django.contrib import admin
from .models import User, Subject, Exam, Question, Choice, StudentExam, Answer


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_active')
    search_fields = ('username', 'email')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'teacher', 'start_date', 'duration_minutes', 'total_score', 'created_at')
    list_filter = ('subject', 'teacher', 'start_date')
    search_fields = ('title', 'subject__name', 'teacher__username')
    date_hierarchy = 'start_date'


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'exam', 'question_type', 'marks')
    list_filter = ('question_type', 'exam')
    search_fields = ('text',)
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('text',)


@admin.register(StudentExam)
class StudentExamAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'is_finished', 'joined_at', 'finished_at')
    list_filter = ('is_finished', 'exam')
    search_fields = ('student__username', 'exam__title')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('student_exam', 'question', 'marks_obtained', 'evaluated')
    list_filter = ('evaluated', 'question__exam')
    search_fields = ('student_exam__student__username', 'question__text')
