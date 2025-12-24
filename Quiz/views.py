import logging
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    TeacherRegistrationForm,
    StudentRegistrationForm,
    ExamForm,
    QuestionForm,
    ChoiceFormSet,
)
from .models import Subject, Exam, Question, StudentExam, Answer


logger = logging.getLogger('quiz')  


def home(request):
    logger.info(f"کاربر {'مهمان' if not request.user.is_authenticated else request.user.username} وارد صفحه اصلی شد. IP: {request.META.get('REMOTE_ADDR')}")
    
    if not request.user.is_authenticated:
        logger.debug("کاربر احراز هویت نشده – ریدایرکت به صفحه لاگین")
        return redirect('Quiz:login')
    
    if request.user.user_type == 'teacher':
        logger.info(f"معلم {request.user.username} به داشبورد معلم ریدایرکت شد.")
        return redirect('Quiz:teacher_dashboard')
    else:
        logger.info(f"دانش‌آموز {request.user.username} به داشبورد دانش‌آموز ریدایرکت شد.")
        return redirect('Quiz:student_dashboard')


def teacher_register(request):
    logger.info(f"کاربر از IP {request.META.get('REMOTE_ADDR')} وارد صفحه ثبت‌نام معلم شد.")
    
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            logger.info(f"معلم جدید با موفقیت ثبت‌نام کرد: username={user.username}, email={user.email}")
            return redirect('Quiz:teacher_dashboard')
        else:
            logger.warning(f"ثبت‌نام معلم ناموفق بود. خطاهای فرم: {form.errors}")
    else:
        form = TeacherRegistrationForm()
        logger.debug("نمایش فرم ثبت‌نام معلم")
    
    return render(request, 'register.html', {'form': form, 'role': 'معلم'})


def student_register(request):
    logger.info(f"کاربر از IP {request.META.get('REMOTE_ADDR')} وارد صفحه ثبت‌نام دانش‌آموز شد.")
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            logger.info(f"دانش‌آموز جدید با موفقیت ثبت‌نام کرد: username={user.username}, email={user.email}")
            return redirect('Quiz:student_dashboard')
        else:
            logger.warning(f"ثبت‌نام دانش‌آموز ناموفق بود. خطاهای فرم: {form.errors}")
    else:
        form = StudentRegistrationForm()
        logger.debug("نمایش فرم ثبت‌نام دانش‌آموز")
    
    return render(request, 'register.html', {'form': form, 'role': 'دانش‌آموز'})


@login_required
def teacher_dashboard(request):
    logger.info(f"معلم {request.user.username} وارد داشبورد شد.")
    
    if request.user.user_type != 'teacher':
        logger.warning(f"کاربر غیرمعلم {request.user.username} ({request.user.user_type}) سعی کرد به داشبورد معلم دسترسی پیدا کند.")
        return redirect('Quiz:student_dashboard')

    exams = Exam.objects.filter(teacher=request.user).prefetch_related(
        'questions', 'studentexam_set__student'
    )

    for exam in exams:
        submitted = exam.studentexam_set.filter(is_finished=True)
        exam.has_submitted = submitted.exists()
        exam.submitted_count = submitted.count()
        exam.first_submission = submitted.first()
        exam.single_submission = exam.submitted_count == 1

    logger.debug(f"معلم {request.user.username} تعداد {exams.count()} آزمون را مشاهده کرد.")
    return render(request, 'teacher/dashboard.html', {'exams': exams})


@login_required
def student_dashboard(request):
    logger.info(f"دانش‌آموز {request.user.username} وارد داشبورد شد.")
    
    if request.user.user_type != 'student':
        logger.warning(f"کاربر غیر دانش‌آموز {request.user.username} سعی کرد به داشبورد دانش‌آموز دسترسی پیدا کند.")
        return redirect('Quiz:teacher_dashboard')

    enrolled = StudentExam.objects.filter(student=request.user)
    available_exams = Exam.objects.exclude(studentexam__student=request.user)

    query = request.GET.get('subject')
    if query:
        available_exams = available_exams.filter(subject__name__icontains=query)
        logger.debug(f"دانش‌آموز {request.user.username} آزمون‌ها را با جستجوی درس '{query}' فیلتر کرد.")

    return render(request, 'student/dashboard.html', {
        'enrolled_exams': enrolled,
        'available_exams': available_exams,
        'subjects': Subject.objects.all()
    })


@login_required
def subject_list(request):
    logger.info(f"معلم {request.user.username} لیست دروس را مشاهده کرد.")
    
    if request.user.user_type != 'teacher':
        logger.warning(f"کاربر غیرمعلم سعی کرد لیست دروس را ببیند.")
        return redirect('Quiz:student_dashboard')
    
    subjects = Subject.objects.all()
    return render(request, 'teacher/subject_list.html', {'subjects': subjects})


@login_required
def create_subject(request):
    logger.info(f"معلم {request.user.username} وارد صفحه ایجاد درس شد.")
    
    if request.user.user_type != 'teacher':
        logger.warning(f"کاربر غیرمعلم سعی کرد درس ایجاد کند.")
        return redirect('Quiz:student_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Subject.objects.create(name=name.strip(), description=description)
            logger.info(f"درس جدید ایجاد شد: '{name}' توسط {request.user.username}")
            messages.success(request, f'درس "{name}" با موفقیت ایجاد شد.')
            return redirect('Quiz:subject_list')
        else:
            logger.warning("تلاش برای ایجاد درس بدون نام.")

    return render(request, 'teacher/create_subject.html')


@login_required
def create_exam(request):
    logger.info(f"معلم {request.user.username} وارد صفحه ایجاد آزمون شد.")
    
    if request.user.user_type != 'teacher':
        logger.warning(f"کاربر غیرمعلم {request.user.username} سعی کرد آزمون ایجاد کند.")
        return redirect('Quiz:student_dashboard')

    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
            logger.info(f"آزمون جدید ایجاد شد: '{exam.title}' (ID: {exam.id}) توسط {request.user.username}")
            messages.success(request, 'آزمون با موفقیت ایجاد شد.')
            return redirect('Quiz:add_questions', exam.id)
        else:
            logger.error(f"خطا در فرم ایجاد آزمون توسط {request.user.username}: {form.errors}")
    else:
        form = ExamForm()
        logger.debug("نمایش فرم ایجاد آزمون")

    return render(request, 'teacher/create_exam.html', {'form': form})


@login_required
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    logger.info(f"معلم {request.user.username} وارد صفحه ویرایش آزمون {exam.title} (ID: {exam.id}) شد.")
    
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            logger.info(f"آزمون '{exam.title}' با موفقیت ویرایش شد توسط {request.user.username}")
            messages.success(request, 'آزمون با موفقیت ویرایش شد.')
            return redirect('Quiz:teacher_dashboard')
        else:
            logger.error(f"خطا در ویرایش آزمون {exam.id}: {form.errors}")
    else:
        form = ExamForm(instance=exam)

    return render(request, 'teacher/edit_exam.html', {'form': form, 'exam': exam})


@login_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    logger.info(f"معلم {request.user.username} وارد صفحه حذف آزمون {exam.title} (ID: {exam.id}) شد.")
    
    if request.method == 'POST':
        exam.delete()
        logger.info(f"آزمون '{exam.title}' (ID: {exam.id}) با موفقیت حذف شد توسط {request.user.username}")
        messages.success(request, 'آزمون حذف شد.')
        return redirect('Quiz:teacher_dashboard')
    
    return render(request, 'teacher/delete_exam.html', {'exam': exam})


@login_required
def add_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    logger.info(f"معلم {request.user.username} وارد صفحه افزودن سوال به آزمون {exam.title} شد.")
    
    ChoiceFormSetFactory = ChoiceFormSet

    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.exam = exam
            question.save()

            if question.question_type == 'mcq':
                formset = ChoiceFormSetFactory(request.POST, instance=question)
                if formset.is_valid():
                    formset.save()
                    logger.info(f"سوال چندگزینه‌ای جدید به آزمون {exam.id} اضافه شد (ID سوال: {question.id})")
                else:
                    logger.error(f"خطا در فرم‌ست گزینه‌ها: {formset.errors}")
            else:
                logger.info(f"سوال غیرچندگزینه‌ای جدید به آزمون {exam.id} اضافه شد (نوع: {question.question_type})")

            messages.success(request, 'سوال اضافه شد.')
            return redirect('Quiz:add_questions', exam.id)
    else:
        question_form = QuestionForm()
        formset = ChoiceFormSetFactory()

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
    logger.info(f"معلم {request.user.username} وارد ویرایش سوال {question.id} از آزمون {question.exam.title} شد.")
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()

            if question.question_type == 'mcq':
                formset = ChoiceFormSet(request.POST, instance=question)
                if formset.is_valid():
                    formset.save()
                else:
                    logger.error(f"خطا در ویرایش گزینه‌ها: {formset.errors}")

            logger.info(f"سوال {question.id} با موفقیت ویرایش شد.")
            messages.success(request, 'سوال ویرایش شد.')
            return redirect('Quiz:add_questions', question.exam.id)
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question) if question.question_type == 'mcq' else ChoiceFormSet()

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
    logger.info(f"معلم {request.user.username} وارد صفحه حذف سوال {question.id} شد.")
    
    if request.method == 'POST':
        question.delete()
        logger.info(f"سوال {question.id} با موفقیت حذف شد.")
        messages.success(request, 'سوال حذف شد.')
        return redirect('Quiz:add_questions', exam_id)
    
    return render(request, 'teacher/delete_question.html', {'question': question})


@login_required
def enroll_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    logger.info(f"دانش‌آموز {request.user.username} در آزمون '{exam.title}' (ID: {exam.id}) ثبت‌نام کرد.")
    
    if request.user.user_type != 'student':
        logger.warning(f"کاربر غیر دانش‌آموز {request.user.username} سعی کرد در آزمون ثبت‌نام کند.")
        return redirect('Quiz:teacher_dashboard')

    student_exam, created = StudentExam.objects.get_or_create(student=request.user, exam=exam)
    if created:
        student_exam.started_at = timezone.now()
        student_exam.save()
        logger.info(f"دانش‌آموز {request.user.username} آزمون را شروع کرد.")

    return redirect('Quiz:take_exam', student_exam.id)


@login_required
def take_exam(request, student_exam_id):
    student_exam = get_object_or_404(
        StudentExam,
        id=student_exam_id,
        student=request.user,
        is_finished=False
    )
    exam = student_exam.exam
    logger.info(f"دانش‌آموز {request.user.username} در حال پاسخ به آزمون '{exam.title}' (StudentExam ID: {student_exam.id}) است.")

    if not student_exam.started_at:
        student_exam.started_at = timezone.now()
        student_exam.save(update_fields=['started_at'])
        logger.debug(f"زمان شروع آزمون برای {request.user.username} ثبت شد.")

    
    elapsed = timezone.now() - student_exam.started_at
    duration = timezone.timedelta(minutes=exam.duration_minutes)
    remaining_time = duration - elapsed
    time_up = remaining_time <= timezone.timedelta(seconds=0)

    if request.method == "POST" or time_up:
        logger.info(f"آزمون {exam.title} توسط {request.user.username} ارسال شد ({'زمان تمام شد' if time_up else 'ارسال دستی'}).")

        for question in exam.questions.all():
            answer, _ = Answer.objects.get_or_create(
                student_exam=student_exam,
                question=question
            )
            

            if question.question_type == 'mcq' and not answer.evaluated:
                answer.auto_grade()

        student_exam.calculate_final_score()
        student_exam.mark_as_finished()
        logger.info(f"نمره نهایی دانش‌آموز {request.user.username}: {student_exam.final_score}")

        messages.success(request, "آزمون با موفقیت ارسال شد!")
        return redirect('Quiz:exam_result', student_exam.id)

    logger.debug(f"زمان باقی‌مانده برای {request.user.username}: {int(remaining_time.total_seconds())} ثانیه")
    

    questions = exam.questions.prefetch_related('choices').all()
    

    return render(request, 'student/take_exam.html', context)


@login_required
def exam_result(request, student_exam_id):
    student_exam = get_object_or_404(StudentExam, id=student_exam_id, student=request.user)
    logger.info(f"دانش‌آموز {request.user.username} نتایج آزمون {student_exam.exam.title} را مشاهده کرد. نمره: {student_exam.final_score}")
    
    return render(request, 'student/result.html', {'student_exam': student_exam})


@login_required
def grade_student_answers(request, student_exam_id):
    student_exam = get_object_or_404(
        StudentExam,
        id=student_exam_id,
        exam__teacher=request.user,
        is_finished=True
    )
    logger.info(f"معلم {request.user.username} وارد صفحه تصحیح پاسخ‌های {student_exam.student.username} برای آزمون {student_exam.exam.title} شد.")

    if request.method == 'POST':
        
        student_exam.calculate_final_score()
        logger.info(f"نمرات دانش‌آموز {student_exam.student.username} توسط معلم {request.user.username} ثبت شد. نمره نهایی: {student_exam.final_score}")
        messages.success(request, f"نمرات {student_exam.student} با موفقیت ثبت شد.")
        return redirect('Quiz:grade_exam', student_exam.exam.id)

    return render(request, 'teacher/grade_student_answers.html', {
        'student_exam': student_exam,
        'answers_to_grade': student_exam.answers.filter(
            question__question_type__in=['short', 'long', 'file']
        ).select_related('question')
    })


@login_required
def grade_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, teacher=request.user)
    logger.info(f"معلم {request.user.username} لیست تصحیح آزمون {exam.title} را مشاهده کرد.")
    
    student_exams = StudentExam.objects.filter(
        exam=exam,
        is_finished=True
    ).select_related('student').order_by('-finished_at')

    return render(request, 'teacher/grade_exam.html', {
        'exam': exam,
        'student_exams': student_exams,
    })


def user_logout(request):
    logger.info(f"کاربر {request.user.username if request.user.is_authenticated else 'مهمان'} از سیستم خارج شد. IP: {request.META.get('REMOTE_ADDR')}")
    logout(request)
    return redirect('Quiz:login')