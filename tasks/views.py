from django.http import JsonResponse , HttpResponse
from .models import Task, Employee,ChatMessage,UserLogin,Notification
from django.utils.timezone import now
import re,os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate,login,logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import UserRegistrationForm, UserLoginForm, EmployeeLoginForm, TaskForm
import json
from django.contrib.auth.hashers import check_password ,make_password
from django.contrib.auth.forms import PasswordChangeForm

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('employee_dashboard')  
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login') 

def signup_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account has been created successfully. Please log in.")
            return redirect("login")
        else:
            messages.error(request, "An error occurred. Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, "signup.html", {"form": form})

def home(request):
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='Completed').count()
    pending_tasks = total_tasks - completed_tasks

    high_priority = Task.objects.filter(priority='High').count() 
    medium_priority = Task.objects.filter(priority='Medium').count()
    low_priority = Task.objects.filter(priority='Low').count()
    
    # current_time = datetime.now()
    chart_data = {
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
    }

    return render(request, 'home.html', {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'chart_data': chart_data,
        # 'current_time': current_time,
    })


def add_task(request):
    employees = Employee.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        priority = request.POST.get('priority')
        deadline = request.POST.get('deadline')
        duration = request.POST.get('duration', 0)
        recurring = request.POST.get('recurring') == 'on'
        notes = request.POST.get('notes', '')
        assigned_employee_id = request.POST.get('employee')
        upload_file = request.FILES.get('pdf_file')

        name_pattern = r'^[A-Za-z\s-]+$'
        if not re.match(name_pattern, name):
            messages.error(request, 'Name can only contain letters and spaces.')
            return render(request, 'add_task.html', {'employees': employees})

        # ✅ Check file extension
        if upload_file:
            ext = os.path.splitext(upload_file.name)[1].lower()
            if ext != '.pdf':
                messages.error(request, 'Only PDF files are allowed.')
                return render(request, 'add_task.html', {'employees': employees})

        try:
            deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
            if deadline_date <= now().date():
                messages.error(request, 'Deadline must be greater than the current date.')
                return render(request, 'add_task.html', {'employees': employees})

            assigned_employee = Employee.objects.get(id=assigned_employee_id)

            Task.objects.create(
                name=name,
                priority=priority,
                deadline=deadline_date,
                duration=duration,
                recurring=recurring,
                notes=notes,
                assigned_employee=assigned_employee,
                assigned_date=now(),
                pdf_file=upload_file
            )

            messages.success(request, 'Task added successfully!')
            return redirect('home')

        except ValueError:
            messages.error(request, 'Invalid date format. Please enter a valid deadline.')
            return render(request, 'add_task.html', {'employees': employees})

        except Employee.DoesNotExist:
            messages.error(request, 'The selected employee does not exist.')

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return render(request, 'add_task.html', {'employees': employees})



def view_schedule(request):
    view_type = request.GET.get('view', 'daily').lower()
    search_query = request.GET.get('search', '').strip()
    tasks = Task.objects.all()

    if search_query:
        tasks = tasks.filter(name__icontains=search_query)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        task_list = [
            {
                "id": task.id,
                "name": task.name,
                "priority": task.priority,
                "status": task.status,
                "deadline": task.deadline.strftime("%Y-%m-%d %H:%M"),
                "assigned_employee": task.assigned_employee.name if task.assigned_employee else None,
            }
            for task in tasks
        ]
        return JsonResponse({"tasks": task_list})

    return render(request, 'view_schedule.html', {'tasks': tasks, 'view_type': view_type, 'search_query': search_query})


def task_analytics(request):
    completed_tasks = Task.objects.filter(status='Completed').count()
    pending_tasks = Task.objects.filter(status='Pending').count()
    overdue_tasks = Task.objects.filter(deadline__lt=datetime.now(), status='Pending').count()

    data = {
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'overdue_tasks': overdue_tasks
    }
    
    return JsonResponse(data)

def analytics(request):
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='Completed').count()
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks else 0

    completion_data = {
        "labels": ["Completed", "Pending"],
        "datasets": [{
            "data": [completed_tasks, total_tasks - completed_tasks],
            "backgroundColor": ['#FF6384', '#FFCE56', '#36A2EB']
        }]
    }

    priorities = Task.objects.values('priority').annotate(count=Count('priority'))
    priority_labels = [p['priority'] for p in priorities]
    priority_values = [p['count'] for p in priorities]
    priority_data = {
        "labels": priority_labels,
        "datasets": [{
            "data": priority_values,
            "backgroundColor": ['#FF6384', '#FFCE56', '#36A2EB'],

        }]
    }

    priority_trends = Task.objects.values('deadline', 'priority').annotate(count=Count('id'))
    deadlines = sorted(set([t['deadline'].strftime('%Y-%m-%d') for t in priority_trends]))
    priority_levels = ['High', 'Medium', 'Low']

    datasets = []
    colors = {'High': '#FF5733', 'Medium': '#FFC300', 'Low': '#33FF57'}
    for priority in priority_levels:
        data = [
            next((t['count'] for t in priority_trends if t['priority'] == priority and t['deadline'].strftime('%Y-%m-%d') == date), 0)
            for date in deadlines
        ]
        datasets.append({
            'label': priority,
            'data': data,
            'borderColor': colors[priority],
            'fill': False,
        })

    trend_data = {
        "labels": deadlines,
        "datasets": datasets,
    }

    context = {
        'completion_data': completion_data,
        'priority_data': priority_data,
        'trend_data': trend_data,
    }

    return render(request, 'analytics.html', context)

def task_stats(request):
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(is_completed=True).count()
    pending_tasks = total_tasks - completed_tasks

    high_priority = Task.objects.filter(priority=1).count()
    medium_priority = Task.objects.filter(priority=2).count()
    low_priority = Task.objects.filter(priority=3).count()

    stats = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'high_priority': high_priority, 
        'medium_priority': medium_priority,
        'low_priority': low_priority,
    }
    
    return JsonResponse(stats)

# def edit_task(request, task_id):
#     task = get_object_or_404(Task, id=task_id)
    
#     if request.method == 'POST':
#         form = TaskForm(request.POST, request.FILES, instance=task)
#         if form.is_valid():
#             form.save()
#             return redirect('view-schedule')
#     else:
#         form = TaskForm(instance=task)
    
#     return render(request, 'edit_task.html', {'form': form, 'task': task})

def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task)

        if form.is_valid():
            print("✅ Cleaned Data:")
            for field in form.cleaned_data:
                print(f"{field}: {form.cleaned_data[field]}")  # हे पाहून confirm होईल data change झाला का

            form.save()
            print("✅ Task updated successfully")
            return redirect('view_schedule')
        else:
            print("❌ Form is not valid:")
            print(form.errors)
    else:
        form = TaskForm(instance=task)

    return render(request, 'edit_task.html', {'form': form, 'task': task})



def delete_task_view(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        task.delete()
        return redirect('view_schedule')
    return render(request, 'view_schedule.html', {'task': task})

def reschedule_tasks():
    tasks = Task.objects.filter(status="Pending").order_by('priority', 'deadline')
    schedule = []
    current_time = datetime.now()

    for task in tasks:
        task_duration = task.duration if task.duration else 1

        start_time = current_time
        for scheduled_task in schedule:
            if scheduled_task['end_time'] > current_time:
                start_time = max(start_time, scheduled_task['end_time'])

        end_time = start_time + timedelta(hours=task_duration)

        schedule.append({
            'task': task,
            'start_time': start_time,
            'end_time': end_time,
            'status': task.status 
        })

        current_time = end_time  

    return schedule


def get_schedule_api(request):
    tasks = Task.objects.all()
    try:
        schedule = reschedule_tasks()
        if not schedule:
            return JsonResponse({'schedule': [], 'message': 'No tasks scheduled yet.'}, status=200)

        response = []
        for item in schedule:
            task = item.get('task')
            start_time = item.get('start_time')
            end_time = item.get('end_time')
            status = item.get('status', 'Pending')

            if not task or not start_time or not end_time:
                continue
            
            response.append({
                "task": task.name,
                "priority": task.priority,
                "status": status,
                "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(start_time, datetime) else "N/A",
                "end_time": task.deadline.strftime('%Y-%m-%d %H:%M:%S') if isinstance(start_time, datetime) else "N/A",
            })

        return JsonResponse({'schedule': response}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# @login_required(login_url='employee_login')
def employee_dashboard(request):
    employee_id = request.session.get("employee_id") 

    if not employee_id:
        messages.error(request, "You must be logged in!")
        return redirect("employee_login")

    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found! Please log in again.")
        return redirect("employee_login")

    tasks = Task.objects.filter(assigned_employee=employee).order_by("id")

    completed_tasks = tasks.filter(status__iexact='Completed')
    pending_tasks = tasks.filter(status__iexact='Pending')

    context = {
        'employee': employee,
        'tasks': tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'tasks_count': tasks.count(),
        'completed_tasks_count': completed_tasks.count(),
        'pending_tasks_count': pending_tasks.count(),
    }

    return render(request, 'employee_dashboard.html', context)


def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
    if request.method == 'POST':
        task.status = request.POST.get('status')
        task.save()
        return redirect('employee_dashboard')
    return render(request, 'update_task_status.html', {'task': task})

def my_task(request):
    employee = get_object_or_404(Employee, email=request.user.email)
    tasks = Task.objects.filter(assigned_employee=employee).order_by('-deadline')

    completed_tasks = tasks.filter(status='Completed')
    pending_tasks = tasks.filter(status='Pending')

    context = {
        'tasks': tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'tasks_count': tasks.count(),
        'completed_tasks_count': completed_tasks.count(),
        'pending_tasks_count': pending_tasks.count(),
    }

    return render(request, 'my_task.html', context)

# def delete_task(request, task_id):
#     if request.method == "POST":
#         task = get_object_or_404(Task, id=task_id)
#         task.delete()
#         messages.success(request, "Task deleted successfully.")
#         return JsonResponse({"success": True, "message": "Task deleted successfully."})
#     return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)

def task_detail(request, task_id):
    if request.method == "POST":
        task = get_object_or_404(Task, id=task_id)
        new_status = request.POST.get("status")

        if new_status in ["Pending", "Completed"]:
            task.status = new_status
            task.save()
            messages.success(request, "Task status updated successfully!")
        else:
            messages.error(request, "Invalid status value.")

        return redirect("employee_dashboard")

    return redirect("employee_dashboard")

def add_employee(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        position = request.POST.get('position', '').strip()
        department = request.POST.get('department', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('employee_image')
        new_password = request.POST.get('password')

        name_pattern = r'^[A-Za-z\s]+$' 
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z.-]+\.[a-zA-Z]{2,}$'
        phone_pattern = r'^\d{10}$' 
        allowed_extensions = ['jpeg', 'jpg', 'png']

        if not all([name, email, position, department]):
            messages.error(request, 'Name, Email, Position, and Department are required fields.')
            return render(request, 'add_employee.html')

        if not re.match(name_pattern, name):
            messages.error(request, 'Name can only contain letters and spaces.')
            return render(request, 'add_employee.html')

        if not re.match(email_pattern, email):
            messages.error(request, 'Invalid email format.')
            return render(request, 'add_employee.html')

        if Employee.objects.filter(email=email).exists():
            messages.error(request, 'An employee with this email already exists.')
            return render(request, 'add_employee.html')

        if phone_number and not re.match(phone_pattern, phone_number):
            messages.error(request, 'Phone number must be exactly 10 digits.')
            return render(request, 'add_employee.html')

        if Employee.objects.filter(phone_number = phone_number).exists():
            messages.error(request, 'An employee with this mobile number already exists.')
            return render(request, 'add_employee.html')
        
        if image:
            file_extension = image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                messages.error(request, 'Only JPEG, JPG, and PNG files are allowed.')
                return render(request, 'add_employee.html')
        else:
            image = 'employees/default.png'

        # hashed_password = make_password(new_password)

        try:
            employee = Employee(
                name=name,
                email=email,
                position=position,
                department=department,
                phone_number=phone_number,
                is_active=is_active,
                image=image,
                password = new_password
            )
            employee.save()
            messages.success(request, 'Employee added successfully!')
            return redirect('add_employee')
        except Exception as e:
            messages.error(request, f'Error adding employee: {e}')

    return render(request, 'add_employee.html')

def view_employees(request):
    employees = Employee.objects.all().order_by('-date_joined')
    return render(request, 'view_employees.html', {'employees': employees})

def update_employee(request, id):
    if request.method == 'POST':
        try:

            employee = get_object_or_404(Employee, id=id)
            new_position = request.POST.get('position')
            new_department = request.POST.get('department')

            if new_position and new_department:
                employee.position = new_position
                employee.department = new_department
                employee.save()
                return JsonResponse({'success': True, 'message': 'Employee updated successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid data received'}, status=400)

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)

def delete_employee(request, employee_id):
    if request.method == 'POST':
        employee = get_object_or_404(Employee, id=employee_id)
        employee.delete()
        return JsonResponse({'message': 'Employee deleted successfully'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == "POST":
        new_status = request.POST.get('status')
        task.status = new_status
        task.save()
        return redirect('task_detail', task_id=task.id)
    
    return render(request, 'task_detail.html', {'task': task})

def employee_profile(request):
    employee = get_object_or_404(Employee, id=1)
    tasks = employee.tasks.all() if hasattr(employee, 'tasks') else []
    context = {
        'employee': employee,
        'tasks': tasks,
    }
    return render(request, 'employee_profile.html', context)

def register_user(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "User registered successfully!")
            return redirect('admin_login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def admin_login(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            try:
                user = UserLogin.objects.get(username=username, password=password)
                request.session['user_id'] = user.id
                messages.success(request, "Logged in successfully!")
                return redirect('home')
            except UserLogin.DoesNotExist:
                messages.error(request, "Invalid username or password.")
    else:
        form = UserLoginForm()
    return render(request, 'admin_login.html', {'form': form})

def logout_user(request):
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect('admin_login')

def get_notifications(request):
    if not request.user.is_authenticated:
        return render(request, 'notifications.html', {'notifications': []})

    now = timezone.now()
    
    intervals = [
        ("1 hour", timedelta(hours=1)),
        ("2 hours", timedelta(hours=2)),
        ("12 hours", timedelta(hours=12)),
        ("24 hours", timedelta(hours=24)),
        ("1 week", timedelta(weeks=1)),
        ("1 month", timedelta(weeks=4)),
    ]
    
    notifications_data = []
    
    for label, delta in intervals:
        time_threshold = now - delta
        
        notifications_qs = Notification.objects.filter(
            user=request.user,
            is_read=False,
            created_at__gte=time_threshold
        ).order_by('-created_at')

        if notifications_qs.exists():
            notifications_data.append({
                "interval": label,
                "notifications": [
                    {"id": n.id, "message": n.message, "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")}
                    for n in notifications_qs
                ],
                "count": notifications_qs.count(),
            })

    return render(request, 'notifications.html', {'notifications': notifications_data})

def send_task_reminders():
    now = timezone.now()
    upcoming_tasks = Task.objects.filter(status="Pending", deadline__lte=now + timedelta(hours=12))

    if not upcoming_tasks.exists():
        return 

    notifications_to_create = []
    
    for task in upcoming_tasks:
        message = f"Reminder: Your task '{task.name}' is due on {task.deadline.strftime('%Y-%m-%d %H:%M:%S')}. Please complete it on time."
        
        notifications_to_create.append(
            Notification(user=task.assigned_employee, task=task, message=message)
        )
    
    Notification.objects.bulk_create(notifications_to_create)

def chatbot_response(user_input):
    responses = {
        "hello": "Hi there! How can I assist you?",
        "hi" : "Hi there! How can I assist you?",
        "who are you" : "I'm chatbot. Created by Narendra Sir",
        "how are you": "I'm a bot, but I'm doing great! How about you?",
        "bye": "Goodbye! Have a nice day!",
    }
    return responses.get(user_input.lower(), "I'm sorry, I don't understand that. Please contact your admin..")

def chat_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user_message = data.get("message", "").strip()

            if not user_message:
                return JsonResponse({"error": "Empty message"}, status=400)

            bot_reply = chatbot_response(user_message)
            ChatMessage.objects.create(user_message=user_message, bot_response=bot_reply)

            return JsonResponse({"user_message": user_message, "bot_reply": bot_reply})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

def chat_page(request):
    return render(request, "chat.html")

def about_us(request):
    return render(request,'about_us.html')

def our_employee(request):
    employees = Employee.objects.all()
    return render(request, 'our_employee.html', {'employees': employees})

def Log_out(request):
    logout(request)
    return redirect('login')

def employee_login(request):
    if request.method == "POST":
        form = EmployeeLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                employee = Employee.objects.get(email=email)

                if password == employee.password:  
                    request.session["employee_id"] = employee.id
                    messages.success(request, "Login successful!")
                    return redirect("employee_info")
                else:
                    messages.error(request, "Invalid email or password.")

            except Employee.DoesNotExist:
                messages.error(request, "Invalid email or password.")
            
    else:
        form = EmployeeLoginForm()

    return render(request, "employee_login.html", {"form": form})

def employee_info(request):
    employee_id = request.session.get("employee_id") 
    
    if not employee_id:
        messages.error(request, "You must be logged in!")
        return redirect("employee_login")

    employee = Employee.objects.get(id=employee_id)
    tasks = Task.objects.filter(assigned_employee=employee).order_by("id")

    completed_tasks = tasks.filter(status__iexact="Completed")
    pending_tasks = tasks.filter(status__iexact="Pending")

    context = {
        "employee": employee,
        "tasks": tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "tasks_count": tasks.count(),
        "completed_tasks_count": completed_tasks.count(),
        "pending_tasks_count": pending_tasks.count(),
    }

    return render(request, "employee_dashboard.html", context)

def employee_logout(request):
    request.session.flush() 
    messages.success(request, "Logged out successfully!")
    return redirect("employee_login")

def fetch_messages(request):
    messages_list = request.session.pop("messages", [])
    return JsonResponse({"messages": messages_list})

def download_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="task_report.pdf"'
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, height - 50, "Task Report")

    p.setFont("Helvetica", 12)
    p.drawString(100, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, height - 90, "---------------------------------------------")

    tasks = Task.objects.all().order_by('-deadline')

    y_position = height - 120
    task_number = 1 

    for task in tasks:
        task_description = task.notes if task.notes else "No description provided"

        task_info = (
            f"{task_number}. Task: {task.name} | Priority: {task.priority} | Status: {task.status} "
            f"| Deadline: {task.deadline.strftime('%Y-%m-%d %H:%M')} | Assigned to: {task.assigned_employee if task.assigned_employee else 'Unassigned'}"
        )
        wrapped_task_info = simpleSplit(task_info, "Helvetica", 12, width - 150)
        wrapped_description = simpleSplit(f"Description: {task_description}", "Helvetica", 12, width - 150)

        for line in wrapped_task_info:
            p.drawString(100, y_position, line)
            y_position -= 20 

            if y_position < 50:
                p.showPage()
                p.setFont("Helvetica", 12)
                y_position = height - 50  

        for line in wrapped_description:
            p.drawString(120, y_position, line)
            y_position -= 20

            if y_position < 50:
                p.showPage()
                p.setFont("Helvetica", 12)
                y_position = height - 50  

        task_number += 1 
        y_position -= 15

    p.showPage()
    p.save()
    return response


# setting logic
def settings_view(request):
    return render(request, 'settings.html')

def update_profile(request):
    """Handles profile updates."""
    if request.method == 'POST':
        form = UpdateProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('settings')
    else:
        form = UpdateProfileForm(instance=request.user)

    return render(request, 'update_profile.html', {'form': form})

def change_password(request):
    """Handles password change functionality."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keeps the user logged in
            messages.success(request, "Password changed successfully!")
            return redirect('settings')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'change_password.html', {'form': form})

def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete()  # Deletes the user from the database
        messages.success(request, "Your account has been deleted successfully.")
        logout(request)  # Logs the user out
        return redirect('home')  # Redirect to home page or login page

    return render(request, "delete_account.html")








def view_schedule(request):
    tasks = Task.objects.all().order_by("deadline")  # Sort tasks by nearest deadline
    return render(request, "view_schedule.html", {"tasks": tasks})



