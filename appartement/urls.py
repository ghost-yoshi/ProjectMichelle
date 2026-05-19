from django.urls import path
from .views import (
    accueil,
    feed,
    ajouter_appartement,
    appartement_detail,
    modifier_appartement,
    supprimer_appartement,
    owner_listings,
    admin_dashboard,
    admin_panel,
)

urlpatterns = [
    path('', accueil, name='accueil'),
    path("feed/", feed, name="feed"),
    path("ajouter/", ajouter_appartement, name="owner_publish"),
    path("appartement/<int:pk>/", appartement_detail, name="appartement_detail"),
    path("appartement/<int:id>/modifier/", modifier_appartement, name="modifier_appartement"),
    path("appartement/<int:id>/supprimer/", supprimer_appartement, name="supprimer_appartement"),
    path("prop/", owner_listings, name="owner_listings"),
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),
    path("admin/", admin_panel, name="admin_review"),
]
