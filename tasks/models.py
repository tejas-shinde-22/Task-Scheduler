from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.core.validators import FileExtensionValidator


class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    name = models.CharField(max_length=200, verbose_name='Task Name')
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        verbose_name='Priority Level'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        verbose_name='Task Status'
    )
    deadline = models.DateTimeField(verbose_name='Deadline')
    assigned_date = models.DateField(default=now)
    duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Task Duration (in hours)'
    )
    recurring = models.BooleanField(
        default=False,
        verbose_name='Is Recurring Task'
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name='Additional Notes'
    )
    assigned_employee = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="Assigned Employee"
    )
    
    pdf_file = models.FileField(
    upload_to='task_pdfs/',
    null=True,
    blank=True,
    verbose_name='Task PDF',
    validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )

    def __str__(self):
        return f"Task: {self.name} - {self.status}"

    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['-deadline']

    @property
    def is_overdue(self):
        """Check if the task is overdue."""
        return self.status != 'Completed' and self.deadline < now()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

class Employee(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=now)
    image = models.ImageField(upload_to='employees/', default='employees/default.png')
    password = models.CharField(max_length=255)

    # def save(self, *args, **kwargs):
    #     if not self.password.startswith('pbkdf2_sha256$'):
    #         self.password = make_password(self.password)
    #     super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserLogin(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    
    def __str__(self):
        return self.username

class Subbanker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    mobile = models.CharField(max_length=15, null=True, blank=True)
    creationdate = models.DateTimeField(auto_now_add=True)
    assigned_employee = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="Subbanker",
        verbose_name="Assigned Employee"
    )

    def __str__(self):
        return f"Subbanker: {self.user.username if self.user else 'No User'} | Mobile: {self.mobile or 'N/A'}"
    
class ChatMessage(models.Model):
    user_message = models.TextField()
    bot_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User: {self.user_message} | Bot: {self.bot_response}"
    
    
 