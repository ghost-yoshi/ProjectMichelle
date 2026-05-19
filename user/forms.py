from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Profile


User = get_user_model()

class RegisterForm(forms.Form):

    ROLE_CHOICES = [
        ('CLIENT', 'Je cherche un logement'),
        ('PROPRIETAIRE', 'Je suis propriétaire'),
    ]

    username = forms.CharField(
        label="Nom d'utilisateur",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control"
        })
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
               "class": "form-control"
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
              "class": "form-control",
        })
    )
    confirm_password = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
               "class": "form-control",
        })
    )
    phone = forms.CharField(
        label="Téléphone",
        max_length=15,
        widget=forms.TextInput(attrs={
               "class": "form-control",
        })
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            "class": "mb-4"
        })
    )


    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un utilisateur avec cet email existe déjà.")
        return email


    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise ValidationError("Le mot de passe et la confirmation ne correspondent pas.")
        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            role=self.cleaned_data['role']
        )
        Profile.objects.create(
            user=user,
            phoneNuber=self.cleaned_data['phone']
        )
        return user


class AdminUserForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    role = forms.ChoiceField(
        choices=[
            ('CLIENT', 'Client'),
            ('PROPRIETAIRE', 'Propriétaire'),
            ('ADMIN', 'Admin'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    phone = forms.CharField(required=False, max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un utilisateur avec cet email existe déjà.")
        return email

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            role=self.cleaned_data['role'],
        )
        is_admin = self.cleaned_data['role'] == 'ADMIN'
        user.is_staff = is_admin
        user.is_superuser = is_admin
        user.save(update_fields=['is_staff', 'is_superuser'])
        Profile.objects.create(
            user=user,
            phoneNuber=self.cleaned_data.get('phone', ''),
        )
        return user
