from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Exam, Subject

User = get_user_model()

class ManagerTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='t1', password='p1', user_type='teacher')
        self.student = User.objects.create_user(username='s1', password='p1', user_type='student')

    def test_teacher_manager(self):
        teachers = User.teachers.all()
        self.assertIn(self.teacher, teachers)
        self.assertNotIn(self.student, teachers)

    def test_student_manager(self):
        students = User.students.all()
        self.assertIn(self.student, students)
        self.assertNotIn(self.teacher, students)

class ExamTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teacher', user_type='teacher')
        self.subject = Subject.objects.create(name='Math')
        self.exam = Exam.objects.create(
            teacher=self.user,
            subject=self.subject,
            title='Midterm',
            start_date='2026-02-01 10:00:00',
            duration_minutes=60,
            total_score=100
        )

    def test_exam_str(self):
        self.assertEqual(str(self.exam), 'Midterm - Math')
