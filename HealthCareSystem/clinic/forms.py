# clinic/forms.py
from django import forms
from .models import (
    Patient,
    Appointment,
    Insurance,
    Billing,
    Prescription,
    Drug,
    Report,
    PrescriptionDrug,
    DrugInteraction
)
from django.forms import inlineformset_factory
from django.db.models import Q
from django.core.exceptions import ValidationError

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

class StaffForm(forms.Form):
    name = forms.CharField(max_length=255)
    occupation = forms.ChoiceField(choices=[('doctor', 'Doctor'), ('manager', 'Manager')])
    speciality = forms.CharField(max_length=255, required=False)

class StaffContactForm(forms.Form):
    phone_number = forms.CharField(max_length=15, required=False)
    email = forms.EmailField(required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)


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
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'insurance': forms.Select(attrs={'class': 'form-select'}),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'billing_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    def clean_total_amount(self):
        amt = self.cleaned_data.get('total_amount')
        if amt is not None and amt < 0:
            raise ValidationError("Amount cannot be negative.")
        return amt


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
        ]


class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = [
            'drug_name','drug_type','description','dosage_form','strength',
            'manufacturer','interactions','contraindications','side_effects','warnings'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add bootstrap classes & placeholders to every field
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label,
            })


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['patient', 'billing', 'insurance']

class PrescriptionDrugForm(forms.ModelForm):
    class Meta:
        model = PrescriptionDrug
        fields = [
            'drug',
            'quantity',
            'instructions',
        ]
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
            'instructions': forms.Textarea(attrs={'rows': 2}),
        }

# Create an inline formset to handle multiple PrescriptionDrug entries
PrescriptionDrugFormSet = inlineformset_factory(
    Prescription,
    PrescriptionDrug,
    form=PrescriptionDrugForm,
    extra=1,
    can_delete=True
)
class DrugInteractionForm(forms.ModelForm):
    class Meta:
        model = DrugInteraction
        fields = ['drug_1', 'drug_2', 'interaction_details', 'severity_level', 'alert']
        widgets = {
            'drug_1': forms.Select(attrs={'class': 'form-control', 'disabled': True}),
            'drug_2': forms.Select(attrs={'class': 'form-control', 'disabled': True}),
            'interaction_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the interaction...'
            }),
            'severity_level': forms.Select(attrs={'class': 'form-control'}),
            'alert': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Enter alert message for prescriptions...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For existing instances
        if self.instance and self.instance.pk:
            # Lock drug pair for existing interactions
            self.fields['drug_1'].disabled = True
            self.fields['drug_2'].disabled = True
           
    def clean(self):
        cleaned_data = super().clean()
        
            
        # Ensure drugs are different
        drug_1 = cleaned_data.get('drug_1')
        drug_2 = cleaned_data.get('drug_2')
        if drug_1 and drug_2 and drug_1 == drug_2:
            raise forms.ValidationError("A drug cannot interact with itself!")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Ensure consistent ordering for new entries
        if not instance.pk:
            drug_1, drug_2 = sorted([self.cleaned_data['drug_1'], self.cleaned_data['drug_2']], 
                                  key=lambda x: x.drug_name)
            instance.drug_1 = drug_1
            instance.drug_2 = drug_2
            
        if commit:
            instance.save()
        return instance