from django import forms
import magic,os
from .models import Task , UserLogin,Employee, Subbanker
from django.contrib.auth.hashers import check_password
from django.core.validators import FileExtensionValidator, ValidationError


# class TaskForm(forms.ModelForm):
#     class Meta:
#         model = Task
#         fields = ['name', 'priority', 'status', 'deadline', 'recurring', 'notes', 'assigned_employee','pdf_file']
#         widgets = {
#             'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
#             'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add any additional notes...'}),
#         }

# class TaskForm(forms.ModelForm):
#     deadline = forms.DateTimeField(
#         widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
#         input_formats=['%Y-%m-%dT%H:%M']  
#     )
class TaskForm(forms.ModelForm):
    pdf_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text='Upload PDF files only.'
    )

    deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    class Meta:
        model = Task
        fields = ['name', 'priority', 'status', 'deadline', 'recurring', 'notes', 'assigned_employee', 'pdf_file']

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.fields['priority'].initial = 'Medium'
        self.fields['assigned_employee'].queryset = Employee.objects.all()
        self.fields['assigned_employee'].label = "Assign to Employee"
        def clean_pdf_file(self):
            file = self.cleaned_data.get('pdf_file', None)
            if file:
                ext = os.path.splitext(file.name)[1].lower()
                if ext != '.pdf':
                    raise ValidationError("Only PDF files are allowed.")
                if file.content_type != 'application/pdf':
                    raise ValidationError("Invalid file type. Please upload a valid PDF.")
            return file


class UserRegistrationForm(forms.ModelForm):
    class Meta:
        model = UserLogin
        fields = ['username', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

class UserLoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())
    
class SubbankerForm(forms.ModelForm):
    class Meta:
        model = Subbanker
        fields = ('mobile','assigned_employee')

# class EmployeeForm(forms.ModelForm):
#     class Meta:
#         model = Employee
#         fields = ['name', 'position', 'email', 'phone_number', 'image']

# class UpdateProfileForm(forms.ModelForm):
#     """Form to update user profile details."""
    
#     class Meta:
#         model = UserLogin
#         fields = ['username', 'email', 'first_name', 'last_name']
#         widgets = {
#             'username': forms.TextInput(attrs={'class': 'form-control'}),
#             'password': forms.EmailInput(attrs={'class': 'form-control'}),
#         }
     
class EmployeeLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs ={
        'class': 'form-control',
        'placeholder': 'Enter your email'
    }))

    password = forms.CharField(widget=forms.PasswordInput(attrs ={
    'class': 'form-control',
    'placeholder': 'Enter your password'
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            try:
                employee = Employee.objects.get(email = email)
                if password != employee.password:
                    raise forms.ValidationError("Invalid Email and Password")
            except Employee.DoesNotExist:
                raise forms.ValidationError("Invaid Email and Password")
            
        return cleaned_data
 