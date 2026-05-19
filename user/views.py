"""
User Authentication and Profile Views
Handles login, registration, logout, and user profile management.
"""

from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm
from favoris.models import Favoris
from message.models import Conversation, Message


def login(request):
    """
    Handle user login.
    Authenticates user credential and creates session.
    Redirects to feed on success, redisplays form on failure.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            auth_login(request, user)
            messages.success(request, "Connexion réussie !")
            if user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('feed')
        else:
            messages.error(request, "Identifiants incorrects")

    return render(request, 'login.html')


def register(request):
    """
    Handle user registration.
    Creates new user account and authenticates immediately.
    Redirects to feed after successful registration.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Compte créé avec succès !")
            return redirect('feed')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def logout_view(request):
    """
    Handle user logout.
    Destroys user session and redirects to homepage.
    """
    logout(request)
    return redirect('accueil')


@login_required
def profil(request):
    """
    Display user profile with summary statistics.
    Shows favorites count, conversation count, and unread messages.
    """
    utilisateur = request.user

    conversations = Conversation.objects.filter(
        Q(locataire=utilisateur) | Q(proprietaire=utilisateur)
    )
    favoris_count = Favoris.objects.filter(utilisateur=utilisateur).count()
    messages_non_lus = Message.objects.filter(
        conversation__in=conversations,
        lu=False,
    ).exclude(expediteur=utilisateur).count()

    context = {
        "utilisateur": utilisateur,
        "favoris_count": favoris_count,
        "conversations_count": conversations.count(),
        "messages_non_lus": messages_non_lus,
    }

    return render(request, "tenant_profile.html", context)
