# clinic/views.py
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from .models import Patient, Appointment
from .forms import PatientForm, AppointmentForm

# Home Page
class HomeView(TemplateView):
    template_name = "clinic/home.html"

# Patient Views (previously defined)
class PatientListView(ListView):
    model = Patient
    template_name = 'clinic/patient_list.html'
    context_object_name = 'patients'

class PatientDetailView(DetailView):
    model = Patient
    template_name = 'clinic/patient_detail.html'
    context_object_name = 'patient'

class PatientCreateView(CreateView):
    model = Patient
    form_class = PatientForm
    template_name = 'clinic/patient_form.html'
    success_url = reverse_lazy('patient_list')

class PatientUpdateView(UpdateView):
    model = Patient
    form_class = PatientForm
    template_name = 'clinic/patient_form.html'
    success_url = reverse_lazy('patient_list')

# Appointment Views (previously defined)
class AppointmentListView(ListView):
    model = Appointment
    template_name = 'clinic/appointment_list.html'
    context_object_name = 'appointments'

class AppointmentCreateView(CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'clinic/appointment_form.html'
    success_url = reverse_lazy('appointment_list')

class AppointmentUpdateView(UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'clinic/appointment_form.html'
    success_url = reverse_lazy('appointment_list')

# Additional Pages Using TemplateView
class EHRView(TemplateView):
    template_name = "clinic/ehr.html"

class ProvidersView(TemplateView):
    template_name = "clinic/providers.html"

class BillingView(TemplateView):
    template_name = "clinic/billing.html"

class MedicationView(TemplateView):
    template_name = "clinic/medication.html"

class ReportingView(TemplateView):
    template_name = "clinic/reporting.html"

class ComplianceView(TemplateView):
    template_name = "clinic/compliance.html"
