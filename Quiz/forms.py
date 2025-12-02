from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, Exam, Question, Choice, Answer


class TeacherRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'teacher'
        if commit:
            user.save()
        return user


class StudentRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'student'
        if commit:
            user.save()
        return user


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['subject', 'title', 'description', 'start_date', 'duration_minutes', 'total_score']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_type', 'text', 'marks', 'model_answer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choice_forms = None


class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Choice text'}),
        }


ChoiceFormSet = forms.inlineformset_factory(
    Question, Choice, form=ChoiceForm, extra=4, can_delete=False
)


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['answer_text', 'selected_choice', 'uploaded_file']
        widgets = {
            'answer_text': forms.Textarea(attrs={'rows': 4}),
            'selected_choice': forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        question = kwargs.pop('question', None)
        super().__init__(*args, **kwargs)
        if question:
            if question.question_type == 'mcq':
                self.fields['selected_choice'].queryset = question.choices.all()
                self.fields['selected_choice'].required = True
                self.fields['answer_text'].widget = forms.HiddenInput()
                self.fields['uploaded_file'].widget = forms.HiddenInput()
            elif question.question_type in ['short', 'long']:
                self.fields['answer_text'].required = True
                self.fields['selected_choice'].widget = forms.HiddenInput()
                self.fields['uploaded_file'].widget = forms.HiddenInput()
            elif question.question_type == 'file':
                self.fields['uploaded_file'].required = True
                self.fields['answer_text'].widget = forms.HiddenInput()
                self.fields['selected_choice'].widget = forms.HiddenInput()
