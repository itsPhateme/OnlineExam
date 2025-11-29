# Quiz/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'Quiz'

urlpatterns = [
    path('', views.home, name='home'),                         
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/teacher/', views.teacher_register, name='teacher_register'),
    path('register/student/', views.student_register, name='student_register'),
    path('dashboard/teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('dashboard/student/', views.student_dashboard, name='student_dashboard'),
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.create_subject, name='create_subject'),
    path('exam/create/', views.create_exam, name='create_exam'),
    path('exam/<int:exam_id>/edit/', views.edit_exam, name='edit_exam'),
    path('exam/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),
    path('exam/<int:exam_id>/questions/add/', views.add_questions, name='add_questions'),
    path('question/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('exam/<int:exam_id>/enroll/', views.enroll_exam, name='enroll_exam'),
    path('exam/<int:student_exam_id>/take/', views.take_exam, name='take_exam'),
    path('exam/<int:student_exam_id>/result/', views.exam_result, name='exam_result'),
    path('exam/<int:student_exam_id>/grade/', views.grade_exam, name='grade_exam'),
]