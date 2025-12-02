from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    TeacherRegistrationForm, StudentRegistrationForm,
    ExamForm, QuestionForm, ChoiceFormSet
)
from .models import Subject, Exam, Question, StudentExam


def home(request):
    if not request.user.is_authenticated:
        return redirect('Quiz:login')

    if request.user.user_type == 'teacher':
        return redirect('Quiz:teacher_dashboard')
    else:
        return redirect('Quiz:student_dashboard')


def teacher_register(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('Quiz:teacher_dashboard')
    else:
        form = TeacherRegistrationForm()
    return render(request, 'register.html', {'form': form, 'role': 'معلم'})


def student_register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('Quiz:student_dashboard')
    else:
        form = StudentRegistrationForm()
    return render(request, 'register.html', {'form': form, 'role': 'دانش‌آموز'})


# ===================== داشبورد =====================
@login_required
def teacher_dashboard(request):
    if request.user.user_type != 'teacher':
        return redirect('Quiz:student_dashboard')
    exams = Exam.objects.filter(teacher=request.user)
    return render(request, 'teacher/dashboard.html', {'exams': exams})


@login_required
def student_dashboard(request):
    if request.user.user_type != 'student':
        return redirect('Quiz:teacher_dashboard')

    enrolled = StudentExam.objects.filter(student=request.user)
    available_exams = available_exams = Exam.objects.exclude(studentexam__student=request.user)

    query = request.GET.get('subject')
    if query:
        available_exams = available_exams.filter(subject__name__icontains=query)

    return render(request, 'student/dashboard.html', {
        'enrolled_exams': enrolled,
        'available_exams': available_exams,
        'subjects': Subject.objects.all()
    })


# ===================== مدیریت درس =====================
@login_required
def subject_list(request):
    if request.user.user_type != 'teacher':
        return redirect('Quiz:student_dashboard')
    subjects = Subject.objects.all()
    return render(request, 'teacher/subject_list.html', {'subjects': subjects})


@login_required
def create_subject(request):
    if request.user.user_type != 'teacher':
        return redirect('Quiz:student_dashboard')
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Subject.objects.create(name=name.strip(), description=description)
            messages.success(request, f'درس "{name}" با موفقیت ایجاد شد.')
            return redirect('Quiz:subject_list')
    return render(request, 'teacher/create_subject.html')


# ===================== آزمون =====================
@login_required
def create_exam(request):
    if request.user.user_type != 'teacher':
        return redirect('Quiz:student_dashboard')
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
            messages.success(request, 'آزمون با موفقیت ایجاد شد.')
            return redirect('Quiz:add_questions', exam.id)
    else:
        form = ExamForm()
    return render(request, 'teacher/create_exam.html', {'form': form})


@login_required
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, 'آزمون با موفقیت ویرایش شد.')
            return redirect('Quiz:teacher_dashboard')
    else:
        form = ExamForm(instance=exam)
    return render(request, 'teacher/edit_exam.html', {'form': form, 'exam': exam})


@login_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == 'POST':
        exam.delete()
        messages.success(request, 'آزمون حذف شد.')
        return redirect('Quiz:teacher_dashboard')
    return render(request, 'teacher/delete_exam.html', {'exam': exam})


@login_required
def add_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    QuestionFormSet = ChoiceFormSet

    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.exam = exam
            question.save()
            if question.question_type == 'mcq':
                formset = ChoiceFormSet(request.POST, instance=question)
                if formset.is_valid():
                    formset.save()
            messages.success(request, 'سوال اضافه شد.')
            return redirect('Quiz:add_questions', exam.id)
    else:
        question_form = QuestionForm()
        formset = ChoiceFormSet()

    questions = exam.questions.all()
    return render(request, 'teacher/add_questions.html', {
        'exam': exam,
        'question_form': question_form,
        'formset': formset,
        'questions': questions
    })


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id, exam__teacher=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()
            if question.question_type == 'mcq':
                formset = ChoiceFormSet(request.POST, instance=question)
                if formset.is_valid():
                    formset.save()
            messages.success(request, 'سوال ویرایش شد.')
            return redirect('Quiz:add_questions', question.exam.id)
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)

    return render(request, 'teacher/edit_question.html', {
        'form': form,
        'formset': formset,
        'question': question,
        'exam': question.exam
    })


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id, exam__teacher=request.user)
    exam_id = question.exam.id
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'سوال حذف شد.')
        return redirect('Quiz:add_questions', exam_id)
    return render(request, 'teacher/delete_question.html', {'question': question})


# ===================== شرکت در آزمون =====================
@login_required
def enroll_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.user.user_type != 'student':
        return redirect('Quiz:teacher_dashboard')
    student_exam, created = StudentExam.objects.get_or_create(student=request.user, exam=exam)
    if created:
        student_exam.started_at = timezone.now()
        student_exam.save()
    return redirect('Quiz:take_exam', student_exam.id)


@login_required
def take_exam(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    return render(request, 'student/take_exam.html', {})


@login_required
def exam_result(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    return render(request, 'student/result.html', {'student_exam': student_exam})


@login_required
def grade_exam(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, exam__teacher=request.user)
    answers = student_exam.answers.filter(evaluated=False)

    if request.method == 'POST':
        total = student_exam.score
        for answer in answers:
            marks = request.POST.get(f"marks_{answer.id}")
            if marks is not None:
                answer.marks_obtained = float(marks)
                answer.evaluated = True
                answer.save()
                total += answer.marks_obtained - answer.question.marks  # اصلاح امتیاز
        student_exam.score = total
        student_exam.save()
        messages.success(request, 'نمرات ثبت شد.')
        return redirect('Quiz:teacher_dashboard')

    return render(request, 'teacher/grade_exam.html', {
        'student_exam': student_exam,
        'answers': answers
    })


def user_logout(request):
    logout(request)
    return redirect('Quiz:login')
