from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages


def staff_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:  
            login(request, user)
            return redirect("dashboard")  
        else:
            messages.error(request, "Invalid login or not authorized.")
    return render(request, "staff_login.html")
