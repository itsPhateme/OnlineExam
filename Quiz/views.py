import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .forms import (
    TeacherRegistrationForm,
    StudentRegistrationForm,
    ExamForm,
    QuestionForm,
    ChoiceFormSet,
)
from .models import Subject, Exam, Question, StudentExam, Answer, User, OTP
from .tokens import account_activation_token

logger = logging.getLogger('quiz')


def send_activation_email(request, user, to_email):
    current_site = get_current_site(request)
    mail_subject = 'فعال‌سازی حساب کاربری'
    message = render_to_string('acc_active_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    email.send()


def home(request):
    logger.info(f"Home page visit by {request.user}")
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
            user = form.save(commit=False)
            user.is_active = False  # غیرفعال تا زمان تایید ایمیل
            user.save()

            send_activation_email(request, user, form.cleaned_data.get('email'))

            return HttpResponse('ثبت‌نام انجام شد. لطفاً برای فعال‌سازی حساب، ایمیل خود را چک کنید.')
    else:
        form = TeacherRegistrationForm()

    return render(request, 'register.html', {'form': form, 'role': 'معلم'})


def student_register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            send_activation_email(request, user, form.cleaned_data.get('email'))

            return HttpResponse('ثبت‌نام انجام شد. لطفاً برای فعال‌سازی حساب، ایمیل خود را چک کنید.')
    else:
        form = StudentRegistrationForm()

    return render(request, 'register.html', {'form': form, 'role': 'دانش‌آموز'})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, 'حساب شما فعال شد.')
        return redirect('Quiz:home')
    else:
        return HttpResponse('لینک فعال‌سازی نامعتبر است!')


def verify_sms(request):
    """
    این ویو یک شبیه‌سازی برای سیستم OTP است.
    چون پنل پیامکی متصل نیست، کد را در کنسول چاپ می‌کنیم.
    """
    if request.method == 'POST':
        phone = request.POST.get('phone')
        code_input = request.POST.get('code')

        if phone and not code_input:
            otp, created = OTP.objects.get_or_create(phone=phone)
            otp.generate_code()

            # Mock sending SMS (چاپ در کنسول به جای ارسال واقعی)
            print(f"\n************ SMS ************")
            print(f"To: {phone}")
            print(f"Code: {otp.code}")
            print(f"*****************************\n")

            messages.info(request, f"کد تایید به {phone} ارسال شد (کنسول را چک کنید).")
            return render(request, 'verify_sms.html', {'phone': phone, 'step': 2})


        elif phone and code_input:
            try:
                otp = OTP.objects.filter(phone=phone).last()
                if otp and otp.code == code_input and otp.is_valid():
                    otp.delete()
                    messages.success(request, "شماره موبایل تایید شد!")
                    return redirect('Quiz:home')
                else:
                    messages.error(request, "کد اشتباه یا منقضی شده است.")
                    return render(request, 'verify_sms.html', {'phone': phone, 'step': 2})
            except:
                messages.error(request, "خطایی رخ داد.")

    return render(request, 'verify_sms.html', {'step': 1})


@login_required
def teacher_dashboard(request):
    if request.user.user_type != 'teacher':
        return redirect('Quiz:student_dashboard')
    exams = Exam.objects.filter(teacher=request.user).prefetch_related(
        'questions', 'studentexam_set__student'
    )
    for exam in exams:
        submitted = exam.studentexam_set.filter(is_finished=True)
        exam.has_submitted = submitted.exists()
        exam.submitted_count = submitted.count()
    return render(request, 'teacher/dashboard.html', {'exams': exams})


@login_required
def student_dashboard(request):
    if request.user.user_type != 'student':
        return redirect('Quiz:teacher_dashboard')
    enrolled = StudentExam.objects.filter(student=request.user)
    available_exams = Exam.objects.exclude(studentexam__student=request.user)

    return render(request, 'student/dashboard.html', {
        'enrolled_exams': enrolled,
        'available_exams': available_exams,
        'subjects': Subject.objects.all()
    })


@login_required
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, 'teacher/subject_list.html', {'subjects': subjects})


@login_required
def create_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Subject.objects.create(name=name.strip(), description=description)
            return redirect('Quiz:subject_list')
    return render(request, 'teacher/create_subject.html')


@login_required
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
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
            return redirect('Quiz:teacher_dashboard')
    else:
        form = ExamForm(instance=exam)
    return render(request, 'teacher/edit_exam.html', {'form': form, 'exam': exam})


@login_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    if request.method == 'POST':
        exam.delete()
        return redirect('Quiz:teacher_dashboard')
    return render(request, 'teacher/delete_exam.html', {'exam': exam})


@login_required
def add_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
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
            return redirect('Quiz:add_questions', exam.id)
    else:
        question_form = QuestionForm()
        formset = ChoiceFormSet()
    questions = exam.questions.all()
    return render(request, 'teacher/add_questions.html', {
        'exam': exam, 'question_form': question_form, 'formset': formset, 'questions': questions
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
                if formset.is_valid(): formset.save()
            return redirect('Quiz:add_questions', question.exam.id)
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question) if question.question_type == 'mcq' else ChoiceFormSet()
    return render(request, 'teacher/edit_question.html',
                  {'form': form, 'formset': formset, 'question': question, 'exam': question.exam})


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id, exam__teacher=request.user)
    exam_id = question.exam.id
    if request.method == 'POST':
        question.delete()
        return redirect('Quiz:add_questions', exam_id)
    return render(request, 'teacher/delete_question.html', {'question': question})


@login_required
def enroll_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    student_exam, created = StudentExam.objects.get_or_create(student=request.user, exam=exam)
    if created:
        student_exam.started_at = timezone.now()
        student_exam.save()
    return redirect('Quiz:take_exam', student_exam.id)


@login_required
def take_exam(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user, is_finished=False)
    exam = student_exam.exam
    if not student_exam.started_at:
        student_exam.started_at = timezone.now()
        student_exam.save()

    elapsed = timezone.now() - student_exam.started_at
    remaining_time = timezone.timedelta(minutes=exam.duration_minutes) - elapsed

    if request.method == "POST" or remaining_time.total_seconds() <= 0:
        for question in exam.questions.all():
            answer, _ = Answer.objects.get_or_create(student_exam=student_exam, question=question)

            if question.question_type == 'mcq': answer.auto_grade()

        student_exam.calculate_final_score()
        student_exam.mark_as_finished()
        return redirect('Quiz:exam_result', student_exam.id)

    return render(request, 'student/take_exam.html', {'student_exam': student_exam, 'exam': exam})


@login_required
def exam_result(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    return render(request, 'student/result.html', {'student_exam': student_exam})


@login_required
def grade_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    student_exams = StudentExam.objects.filter(exam=exam, is_finished=True)
    return render(request, 'teacher/grade_exam.html', {'exam': exam, 'student_exams': student_exams})


@login_required
def grade_student_answers(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, exam__teacher=request.user)
    if request.method == 'POST':
        student_exam.calculate_final_score()
        return redirect('Quiz:grade_exam', student_exam.exam.id)
    return render(request, 'teacher/grade_student_answers.html', {'student_exam': student_exam})


def user_logout(request):
    logout(request)
    return redirect('Quiz:login')
