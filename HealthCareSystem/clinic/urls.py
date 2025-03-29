# clinic/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Home page
    path('', views.HomeView.as_view(), name='home'),

    # Patient management
    path('patients/', views.PatientListView.as_view(), name='patient_list'),
    path('patients/new/', views.PatientCreateView.as_view(), name='patient_create'),
    path('patients/<int:pk>/', views.PatientDetailView.as_view(), name='patient_detail'),
    path('patients/<int:pk>/edit/', views.PatientUpdateView.as_view(), name='patient_update'),

    # EHR
    path('ehr/', views.EHRView.as_view(), name='ehr'),

    # Appointment scheduling
    path('appointments/', views.AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/new/', views.AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/<int:pk>/edit/', views.AppointmentUpdateView.as_view(), name='appointment_update'),

    # Healthcare providers
    path('providers/', views.ProvidersView.as_view(), name='providers'),

    # Billing and Claims Management
    path('billing/', views.BillingView.as_view(), name='billing'),

    # Medication Management
    path('medication/', views.MedicationView.as_view(), name='medication'),

    # Reporting and Analytics
    path('reporting/', views.ReportingView.as_view(), name='reporting'),

    # Security and Compliance
    path('compliance/', views.ComplianceView.as_view(), name='compliance'),
]
