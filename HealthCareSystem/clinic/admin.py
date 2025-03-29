from django.contrib import admin
from .models import (
    Patient, PatientContact, StaffDetails, StaffContact, PatientsAssigned, Insurance,
    Billing, Prescription, Drug, PrescriptionDrug, DrugInteraction, Appointment, Report
)

admin.site.register(Patient)
admin.site.register(PatientContact)
admin.site.register(StaffDetails)
admin.site.register(StaffContact)
admin.site.register(PatientsAssigned)
admin.site.register(Insurance)
admin.site.register(Billing)
admin.site.register(Prescription)
admin.site.register(Drug)
admin.site.register(PrescriptionDrug)
admin.site.register(DrugInteraction)
admin.site.register(Appointment)
admin.site.register(Report)
