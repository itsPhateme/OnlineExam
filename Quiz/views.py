from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import models   # ← این خط غایب بوده!
from .forms import (
    TeacherRegistrationForm, StudentRegistrationForm,
    ExamForm, QuestionForm, ChoiceFormSet , Answer , Choice
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
    if not request.user.user_type == 'teacher':  # یا هر شرطی که داری
        return redirect('Quiz:student_dashboard')

    # داخل teacher_dashboard view
    exams = Exam.objects.filter(teacher=request.user).prefetch_related(
        'questions', 'studentexam_set__student'
    )

    for exam in exams:
        submitted = exam.studentexam_set.filter(is_finished=True)
        exam.has_submitted = submitted.exists()
        exam.submitted_count = submitted.count()
        exam.first_submission = submitted.first()
        exam.single_submission = exam.submitted_count == 1

    return render(request, 'teacher/dashboard.html', {
        'exams': exams
    })


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
# views.py — تابع take_exam کامل و بدون باگ

@login_required
def take_exam(request, student_exam_id):
    student_exam = get_object_or_404(
        StudentExam,
        id=student_exam_id,
        student=request.user,
        is_finished=False  # جلوگیری از ورود دوباره بعد از ارسال
    )

    exam = student_exam.exam

    # اگر اولین بار اول هست که وارد صفحه میشه → زمان شروع رو ثبت کن
    if not student_exam.started_at:
        student_exam.started_at = timezone.now()
        student_exam.save(update_fields=['started_at'])

    # محاسبه زمان باقی‌مانده
    time_up = False
    if student_exam.started_at:
        elapsed = timezone.now() - student_exam.started_at
        duration = timezone.timedelta(minutes=exam.duration_minutes)
        if elapsed >= duration:
            time_up = True

    # اگر زمان تموم شده یا کاربر دکمه ارسال رو زده → پاسخ‌ها رو ذخیره و آزمون رو ببسته کن
    if request.method == "POST" or time_up:
        # ذخیره یا به‌روزرسانی پاسخ‌ها
        for question in exam.questions.all():
            answer, created = Answer.objects.get_or_create(
                student_exam=student_exam,
                question=question
            )

            if question.question_type == 'mcq':
                choice_id = request.POST.get(f'question_{question.id}')
                if choice_id:
                    answer.selected_choice_id = choice_id
                # پاک کردن فیلدهای غیرمرتبط
                answer.answer_text = None
                answer.uploaded_file = None

            elif question.question_type in ['short', 'long']:
                answer.answer_text = request.POST.get(f'question_{question.id}', '').strip()
                answer.selected_choice = None
                answer.uploaded_file = None

            elif question.question_type == 'file':
                uploaded_file = request.FILES.get(f'question_{question.id}')
                if uploaded_file:
                    answer.uploaded_file = uploaded_file
                answer.answer_text = None
                answer.selected_choice = None

            answer.save()

            # تصحیح خودکار سوالات چندگزینه‌ای
            if question.question_type == 'mcq' and not answer.evaluated:
                answer.auto_grade()  # این متد marks_obtained و evaluated رو تنظیم می‌کنه

        # محاسبه نمره فعلی (فقط MCQ در این لحظه)
        student_exam.calculate_final_score()

        # بستن آزمون
        student_exam.mark_as_finished()

        # is_finished=True + finished_at=now()
        
        messages.success(request, "آزمون با موفقیت ارسال شد!")
        return redirect('Quiz:exam_result', student_exam.id)

    # GET request — نمایش صفحه آزمون
    questions = exam.questions.prefetch_related('choices').all()

    # دریافت پاسخ‌های قبلی دانش‌آموز (اگر برگشته باشه وسط آزمون)
    answers_dict = {
        ans.question_id: ans for ans in student_exam.answers.select_related('selected_choice').all()
    }

    for question in questions:
        question.current_answer = answers_dict.get(question.id)

    remaining_time = student_exam.time_remaining() if student_exam.started_at else timezone.timedelta(minutes=exam.duration_minutes)

    context = {
        'student_exam': student_exam,
        'exam': exam,
        'questions': questions,
        'time_up': time_up,
        'remaining_seconds': int(remaining_time.total_seconds()),
    }

    return render(request, 'student/take_exam.html', context)

@login_required
def exam_result(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    return render(request, 'student/result.html', {'student_exam': student_exam})

# views.py — اضافه کن این ویو مهم
# views.py → تابع grade_student_answers

@login_required
def grade_student_answers(request, student_exam_id):
    student_exam = get_object_or_404(
        StudentExam,
        id=student_exam_id,
        exam__teacher=request.user,
        is_finished=True
    )

    # فقط سوالاتی که نیاز به تصحیح دستی دارن: short, long, file
    answers_to_grade = student_exam.answers.filter(
        question__question_type__in=['short', 'long', 'file']
    ).select_related('question').order_by('question__id')

    if request.method == 'POST':
        for answer in answers_to_grade:
            mark_key = f'marks_{answer.id}'
            if mark_key in request.POST:
                try:
                    marks = float(request.POST[mark_key])
                    max_marks = answer.question.marks
                    answer.marks_obtained = max(0, min(marks, max_marks))
                    answer.evaluated = True
                    answer.save()
                except (ValueError, TypeError):
                    pass  # اگر ورودی اشتباه بود

        # بعد از تصحیح دستی → نمره نهایی رو دوباره حساب کن
        student_exam.calculate_final_score()
        messages.success(request, f"نمرات {student_exam.student} با موفقیت ثبت شد.")
        return redirect('Quiz:grade_exam', student_exam.exam.id)

    context = {
        'student_exam': student_exam,
        'answers_to_grade': answers_to_grade,
    }
    return render(request, 'teacher/grade_student_answers.html', context)
    
@login_required
def grade_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)

    student_exams = StudentExam.objects.filter(
        exam=exam,
        is_finished=True
    ).select_related('student').order_by('-finished_at')

    # هیچ نیازی به این حلقه نیست!
    # چون needs_grading خودش property هست و همیشه درست کار می‌کنه
    # for se in student_exams:
    #     se.needs_grading = ...   حذف شد

    return render(request, 'teacher/grade_exam.html', {
        'exam': exam,
        'student_exams': student_exams,
    })

def user_logout(request):
    logout(request)
    return redirect('Quiz:login')
