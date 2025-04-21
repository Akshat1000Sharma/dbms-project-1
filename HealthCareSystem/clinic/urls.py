# clinic/urls.py
from django.urls import path
from . import views
from .views import signup_view, login_view, logout_view


urlpatterns = [
    
    # Authentication
    path('signup/', signup_view, name='signup'),
    path('login/',  login_view,  name='login'),
    path('logout/', logout_view, name='logout'),

    # Home
    path('', views.HomeView.as_view(), name='home'),

    # Patient CRUD
    path('patients/',          views.patient_list,   name='patient_list'),
    path('patients/new/',      views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),  
    path('patients/<int:pk>/edit/', views.patient_update, name='patient_update'),
    path('patients/<int:pk>/delete/', views.patient_delete, name='patient_delete'),
     path('patients/<int:pk>/contacts/', views.patient_contact_manage, name='patient_contact_manage'),

    # Appointment CRUD
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/new/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/edit/', views.appointment_update, name='appointment_update'),
    
    # Drug Management
    path('drugs/', views.drug_list, name='drug_list'),
    path('drugs/new/', views.drug_create, name='drug_create'),
    path('drugs/<int:pk>/', views.drug_detail, name='drug_detail'),
    path('drugs/<int:pk>/edit/', views.drug_update, name='drug_update'),
    path('drugs/<int:pk>/delete/', views.drug_delete, name='drug_delete'),

    # Staff CRUD
    path('staff/', views.provider_list, name='provider_list'),
    path('staff/new/', views.provider_create, name='provider_create'),
    path('staff/<int:pk>/', views.provider_detail, name='provider_detail'),
    path('staff/<int:pk>/edit/', views.provider_update, name='provider_update'),
    path('staff/<int:pk>/delete/', views.provider_delete, name='provider_delete'),
    path('staff/<int:pk>/contacts/', views.provider_contact_manage, name='provider_contact_manage'),
    path('staff/<int:staff_id>/assign/', views.assign_doctor, name='assign_doctor'),
    

    # Insurance CRUD
    path('insurance/new/', views.insurance_create, name='insurance_create'),
    path('insurance/', views.insurance_list, name='insurance_list'),
    path('insurance/<int:pk>/', views.insurance_detail, name='insurance_detail'),
    path('insurance/<int:pk>/edit/', views.insurance_update, name='insurance_update'),
    path('insurance/<int:pk>/delete/', views.insurance_delete, name='insurance_delete'),    

    # Billing CRUD
    path('billing/', views.billing_list, name='billing_list'),
    path('billing/new/', views.billing_create, name='billing_create'),
    path('billing/<int:pk>/', views.billing_detail, name='billing_detail'),
    path('billing/<int:pk>/edit/', views.billing_update, name='billing_update'),
    path('billing/<int:pk>/delete/', views.billing_delete, name='billing_delete'),

    # Prescription CRUD
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/new/', views.prescription_create, name='prescription_create'),
    path('prescriptions/<int:pk>/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:pk>/edit/', views.prescription_update, name='prescription_update'),
    path('prescriptions/<int:pk>/delete/', views.prescription_delete, name='prescription_delete'),
    
    # drug interaction check
    path('prescriptions/<int:prescription_id>/drugs/', views.prescription_drugs, name='prescription_drugs'),
    path('check_interactions/', views.check_interactions, name='check_interactions'),
    path('drugs/interactions/new/', views.drug_interaction_create, name='drug_interaction_create'),
    path('drugs/interactions/', views.drug_interaction_list, name='drug_interaction_list'),
    path('drugs/interactions/<int:drug1_id>/<int:drug2_id>/', views.drug_interaction_edit, name='drug_interaction_edit'),

    # Reporting CRUD
    path('reporting/', views.report_list, name='report_list'),
    path('reports/new/', views.report_create, name='report_create'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('reports/<int:pk>/edit/', views.report_update, name='report_update'),
    path('reports/<int:pk>/delete/', views.report_delete, name='report_delete'),
    
    # compliance
    path('compliance/', views.ComplianceView.as_view(), name='compliance'),
    
    # EHR
    path('ehr/', views.EHRView.as_view(), name='ehr'),
    path('ehr/<int:pk>/', views.ehr_detail, name='ehr_detail'),

]
handler403 = 'clinic.views.custom_permission_denied'
handler404 = 'clinic.views.custom_page_not_found'