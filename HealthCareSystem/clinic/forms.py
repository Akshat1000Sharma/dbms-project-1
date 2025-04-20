# clinic/forms.py
from django import forms
from .models import (
    Patient,
    Appointment,
    StaffDetails,
    Insurance,
    Billing,
    Prescription,
    Drug,
    Report,
)

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'patient_name',
            'insurance_info',
            'emergency_contact',
            'ehr_link',
            'feedback_rating',
            'registration_date'
        ]
        widgets = {
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_emergency_contact(self):
        data = self.cleaned_data['emergency_contact']
        if len(data) != 10 or not data.isdigit():
            raise forms.ValidationError("Emergency contact must be 10 digits.")
        return data

    def clean_feedback_rating(self):
        rating = self.cleaned_data['feedback_rating']
        if rating < 1 or rating > 5:
            raise forms.ValidationError("Feedback rating must be between 1 and 5.")
        return rating
    
class PatientContactForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15, 
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+1-555-123-4567'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'placeholder': 'patient@example.com'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '123 Main St, City, Country'}),
        required=False
    )


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'patient', 'staff', 'appointment_date', 'appointment_time',
            'appointment_status', 'booking_method', 'reason_for_visit', 'notes'
        ]
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'appointment_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make staff required to avoid empty or invalid foreign‐key inserts
        self.fields['staff'].required = True


class StaffForm(forms.ModelForm):
    class Meta:
        model = StaffDetails
        fields = ['name', 'occupation', 'speciality']


class InsuranceForm(forms.ModelForm):
    class Meta:
        model = Insurance
        fields = [
            'provider_name',
            'policy_number',
            'treatment_coverage_details',
            'amount_covered'
        ]


class BillingForm(forms.ModelForm):
    class Meta:
        model = Billing
        fields = [
            'patient',
            'insurance',
            'total_amount',
            'payment_status',
            'billing_date'
        ]
        widgets = {
            'billing_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = [
            'patient',
            'staff',
            'diagnoses',
            'treatments',
            'allergies',
            'laboratory_test_results',
            'imaging_studies',
            'dosage_instruction',
            'refill_requests',
            'notes',
            'alert'
        ]


class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = [
            'drug_name',
            'drug_type',
            'description',
            'dosage_form',
            'strength',
            'manufacturer',
            'interactions',
            'contraindications',
            'side_effects',
            'warnings'
        ]


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['patient', 'billing', 'insurance']
