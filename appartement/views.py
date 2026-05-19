"""
Apartment Management Views
Handles apartment listings, details, creation, modification and deletion.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Max

from favoris.models import Favoris
from message.models import Conversation, Message
from user.forms import AdminUserForm
from user.models import User
from .models import Appartement, AppartementImage, Signalement
from .forms import SignalementForm
from .utils import superuser_required


def accueil(request):
    """
    Display public homepage with available apartments.
    Redirects authenticated users to feed.
    """
    if request.user.is_authenticated:
        return redirect('feed')

    appartements = Appartement.objects.filter(
        disponible=True,
        moderation_status='APPROVED',
    ).select_related('proprietaire').prefetch_related('images')
    return render(request, 'accueil.html', {'appartements': appartements})


def ajouter_appartement(request):
    """
    Create a new apartment listing.
    Requires user to be authenticated as property owner.
    Accepts POST with apartment details and multiple images.
    """
    if not request.user.is_authenticated or request.user.role != 'PROPRIETAIRE':
        raise PermissionDenied

    if request.method == 'POST':
        appartement = Appartement.objects.create(
            titre=request.POST.get('titre'),
            type_logement=request.POST.get('type_logement'),
            quartier=request.POST.get('quartier'),
            prix=request.POST.get('prix'),
            description=request.POST.get('description'),
            proprietaire=request.user,
            contact_proprietaire=request.POST.get('contact'),
            moderation_status='PENDING',
        )

        for file in request.FILES.getlist('images'):
            AppartementImage.objects.create(
                appartement=appartement,
                image=file
            )

        return redirect('appartement_detail', pk=appartement.id)

    return render(request, 'owner_publish.html')


def supprimer_appartement(request, id):
    """
    Delete an apartment listing.
    Only owner or admin can delete.
    """
    appartement = get_object_or_404(Appartement, id=id)

    if request.user != appartement.proprietaire and not request.user.is_superuser:
        raise PermissionDenied

    appartement.delete()
    return redirect('feed')


def modifier_appartement(request, id):
    """
    Update apartment details.
    Only owner or admin can modify.
    Non-admin modifications trigger re-moderation.
    """
    appartement = get_object_or_404(Appartement, id=id)

    if request.user != appartement.proprietaire and not request.user.is_superuser:
        raise PermissionDenied

    if request.method == 'POST':
        appartement.titre = request.POST.get('titre')
        appartement.prix = request.POST.get('prix')
        appartement.description = request.POST.get('description')
        if not request.user.is_superuser:
            appartement.moderation_status = 'PENDING'
        appartement.save()

        return redirect('appartement_detail', pk=appartement.id)

    return render(request, 'modifier_appartement.html', {'appartement': appartement})


def appartement_detail(request, pk):
    """
    Display apartment details and enable reporting.
    Any authenticated user can report inappropriate listings.
    """
    appartement = get_object_or_404(Appartement, pk=pk)
    images = [image for image in appartement.images.all() if image.image_url_safe]
    report_form = SignalementForm()

    if request.method == 'POST' and request.user.is_authenticated:
        report_form = SignalementForm(request.POST)
        if report_form.is_valid():
            signalement = report_form.save(commit=False)
            signalement.appartement = appartement
            signalement.auteur = request.user
            signalement.save()
            messages.success(request, 'Signalement envoyé à la modération.')
            return redirect('appartement_detail', pk=appartement.id)

    return render(request, 'appartement_detail.html', {
        'appartement': appartement,
        'images': images,
        'report_form': report_form
    })


def liste_appartements(request):
    """
    List all available apartments with optional filtering.
    Filters by: neighborhood (quartier), type, and max price.
    """
    appartements = Appartement.objects.filter(
        disponible=True,
        moderation_status='APPROVED',
    ).select_related('proprietaire').prefetch_related('images')

    quartier = request.GET.get('quartier')
    type_logement = request.GET.get('type')
    prix_max = request.GET.get('prix')

    if quartier:
        appartements = appartements.filter(quartier__icontains=quartier)

    if type_logement:
        appartements = appartements.filter(type_logement=type_logement)

    if prix_max:
        appartements = appartements.filter(prix__lte=prix_max)

    return render(request, 'feed.html', {'appartements': appartements})


@login_required(login_url='login')
def feed(request):
    """
    Display filtered apartment listings for authenticated users.
    Shows user's recent favorites and messages in sidebar.
    Supports filtering by neighborhood, type, and max price.
    """
    appartements = Appartement.objects.filter(
        disponible=True,
        moderation_status='APPROVED',
    ).select_related('proprietaire').prefetch_related('images').order_by('-date_publication')

    quartier = request.GET.get('quartier')
    type_logement = request.GET.get('type')
    prix_max = request.GET.get('prix')

    if quartier:
        appartements = appartements.filter(quartier__icontains=quartier)
    if type_logement:
        appartements = appartements.filter(type_logement=type_logement)
    if prix_max:
        try:
            prix_max = float(prix_max)
            appartements = appartements.filter(prix__lte=prix_max)
        except ValueError:
            pass

    recent_messages = []
    mes_favoris = []

    if request.user.is_authenticated:
        mes_favoris = (
            Favoris.objects.filter(utilisateur=request.user)
            .select_related('logement', 'logement__proprietaire')
            .order_by('-date_ajout')[:3]
        )
        recent_messages = (
            Message.objects.filter(Q(conversation__locataire=request.user) | Q(conversation__proprietaire=request.user))
            .select_related('conversation', 'conversation__logement', 'expediteur')
            .order_by('-date_envoi')[:3]
        )

    paginator = Paginator(appartements, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)
    pagination_query = query_params.urlencode()
    pagination_prefix = f"{pagination_query}&" if pagination_query else ""

    return render(request, 'feed.html', {
        'appartements': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'visible_pages': paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
        'pagination_prefix': pagination_prefix,
        'mes_favoris': mes_favoris,
        'recent_messages': recent_messages,
    })


@login_required
def dashboard_locataire(request):
    """
    Display tenant dashboard with favorites and conversation metrics.
    """
    mes_favoris = Favoris.objects.filter(utilisateur=request.user).select_related('logement').order_by('-date_ajout')
    favoris_disponibles = mes_favoris.filter(logement__disponible=True).count()
    messages_non_lus = Message.objects.filter(
        conversation__in=Conversation.objects.filter(Q(locataire=request.user) | Q(proprietaire=request.user)),
        lu=False,
    ).exclude(expediteur=request.user).count()

    return render(request, 'dashboard_locataire.html', {
        'favoris': mes_favoris,
        'favoris_count': mes_favoris.count(),
        'favoris_disponibles': favoris_disponibles,
        'conversations_count': Conversation.objects.filter(Q(locataire=request.user) | Q(proprietaire=request.user)).count(),
        'messages_non_lus': messages_non_lus,
    })


@login_required
def dashboard_proprietaire(request):
    """
    Display property owner dashboard with listings and statistics.
    """
    mes_appartements = Appartement.objects.filter(
        proprietaire=request.user
    ).select_related('proprietaire').prefetch_related('images').order_by('-date_publication')

    total = mes_appartements.count()
    disponibles = mes_appartements.filter(disponible=True).count()
    avec_images = mes_appartements.filter(images__isnull=False).distinct().count()

    return render(request, 'dashboard_proprietaire.html', {
        'appartements': mes_appartements,
        'total_appartements': total,
        'disponibles': disponibles,
        'avec_images': avec_images,
    })


@login_required
@superuser_required
def admin_dashboard(request):
    """
    Display admin overview dashboard with system statistics.
    """
    recent_appartements = Appartement.objects.select_related('proprietaire').prefetch_related('images').order_by('-date_publication')[:5]
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_signalements = Signalement.objects.select_related('appartement', 'auteur').order_by('-date_creation')[:5]

    total_users = User.objects.count()
    total_clients = User.objects.filter(role='CLIENT').count()
    total_proprietaires = User.objects.filter(role='PROPRIETAIRE').count()
    total_superusers = User.objects.filter(is_superuser=True).count()
    total_annonces = Appartement.objects.count()
    pending_annonces = Appartement.objects.filter(moderation_status='PENDING').count()
    open_reports = Signalement.objects.filter(statut='OPEN').count()

    return render(request, 'admin_dashboard.html', {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_proprietaires': total_proprietaires,
        'total_superusers': total_superusers,
        'total_annonces': total_annonces,
        'pending_annonces': pending_annonces,
        'open_reports': open_reports,
        'recent_appartements': recent_appartements,
        'recent_users': recent_users,
        'recent_signalements': recent_signalements,
    })


def message(request):
    """
    Redirect to conversations list.
    """
    return redirect('liste_conversations')


@login_required
@superuser_required
def admin_panel(request):
    """
    Administration panel for managing users, apartments, and reports.
    Handles approval/rejection of listings and resolution of user reports.
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_user':
            user_form = AdminUserForm(request.POST, prefix='user')
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Utilisateur créé avec succès.")
                return redirect('admin_review')
        elif action == 'delete_user':
            target_user = get_object_or_404(User, id=request.POST.get('user_id'))
            if target_user != request.user and not target_user.is_superuser:
                target_user.delete()
                messages.success(request, "Utilisateur supprimé.")
                return redirect('admin_review')
        elif action in {'approve_appartement', 'reject_appartement'}:
            appartement = get_object_or_404(Appartement, id=request.POST.get('appartement_id'))
            appartement.moderation_status = 'APPROVED' if action == 'approve_appartement' else 'REJECTED'
            appartement.save(update_fields=['moderation_status'])
            messages.success(request, "Statut de l'annonce mis à jour.")
            return redirect('admin_review')
        elif action in {'review_signalement', 'resolve_signalement'}:
            signalement = get_object_or_404(Signalement, id=request.POST.get('signalement_id'))
            signalement.statut = 'REVIEWED' if action == 'review_signalement' else 'RESOLVED'
            signalement.note_admin = request.POST.get('note_admin', signalement.note_admin)
            signalement.save(update_fields=['statut', 'note_admin'])
            messages.success(request, "Signalement traité.")
            return redirect('admin_review')

    user_form = AdminUserForm(prefix='user')
    pending_appartements = Appartement.objects.filter(moderation_status='PENDING').select_related('proprietaire').prefetch_related('images').order_by('-date_publication')
    recent_appartements = Appartement.objects.select_related('proprietaire').prefetch_related('images').order_by('-date_publication')[:10]
    signalements = Signalement.objects.select_related('appartement', 'auteur').order_by('-date_creation')[:10]
    users = User.objects.order_by('-date_joined')

    return render(request, 'admin_review.html', {
        'total_users': User.objects.count(),
        'total_annonces': Appartement.objects.count(),
        'pending_count': pending_appartements.count(),
        'reports_open_count': signalements.filter(statut='OPEN').count(),
        'pending_appartements': pending_appartements,
        'recent_appartements': recent_appartements,
        'signalements': signalements,
        'users': users,
        'user_form': user_form,
    })


@login_required
def owner_listings(request):
    """
    Display owner's apartment listings with availability status.
    """
    appartements = Appartement.objects.filter(proprietaire=request.user).select_related('proprietaire').prefetch_related('images').order_by('-date_publication')
    return render(request, "owner_listings.html", {
        'appartements': appartements,
        'total_appartements': appartements.count(),
        'disponibles': appartements.filter(disponible=True).count(),
        'indisponibles': appartements.filter(disponible=False).count(),
    })
