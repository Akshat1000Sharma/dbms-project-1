from django import forms
from .models import Patient, Appointment

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'demographic_details', 'insurance_info', 'emergency_contact', 'ehr_link',
            'feedback_rating', 'registration_date'
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
