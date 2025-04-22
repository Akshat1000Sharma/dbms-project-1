# clinic/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from .forms import (
    PatientForm, AppointmentForm, StaffForm, InsuranceForm, PrescriptionDrugForm,
    BillingForm, PrescriptionForm, DrugForm, ReportForm, PatientContactForm, StaffContactForm, DrugInteractionForm
)
from .db_utils import (
    list_records, get_record, create_record, update_record
)
import logging
from itertools import combinations
from django.core.paginator import Paginator
from django.utils import timezone
from .models import Appointment, PrescriptionDrug, Prescription, Drug, DrugInteraction
from django.http import JsonResponse, Http404
from django.forms import inlineformset_factory
from django.db.models import Q

# appointment imports
from django.core.mail import send_mail
from django.conf import settings
from .db_utils import list_records


# user authentication imports
from django.db import connection, IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.shortcuts import render
# prescription imports
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from .db_utils import list_records, get_record, create_record, update_record, check_interactions_for_drugs
from .forms import PrescriptionForm, DrugForm, PrescriptionDrugFormSet
from django.contrib import messages

def is_doctor(user):
    # Adjust based on your user model's structure
    return user.is_authenticated and user.role == 'Doctor'

def custom_permission_denied(request, exception=None):
    return render(request, 'clinic/403.html', status=403)

def custom_page_not_found(request, exception=None):
    return render(request, 'clinic/404.html', status=404)

# 1) Home / Static pages
#
class HomeView(TemplateView):
    template_name = "clinic/home.html"

class EHRView(TemplateView):
    template_name = "clinic/ehr.html"


class MedicationView(TemplateView):
    template_name = "clinic/medication.html"




# -----------------------------------------------
# Patient Management Views
def patient_list(request):
    # Get patients with their assigned doctors
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.*,
                s.name AS doctor_name
            FROM Patient p
            LEFT JOIN Patients_Assigned pa ON p.patient_id = pa.patient_id
            LEFT JOIN Staff_Details s ON pa.staff_id = s.staff_id AND s.occupation = 'doctor'
        """)
        cols = [col[0] for col in cursor.description]
        patients = [dict(zip(cols, row)) for row in cursor.fetchall()]

    # Existing contact check
    for patient in patients:
        contacts = list_records('Patient_Contact', where='patient_id = %s', params=[patient['patient_id']])
        patient['has_contacts'] = any(
            contacts and 
            (contacts[0]['phone_number'].strip() or 
             contacts[0]['email'].strip() or 
             contacts[0]['address'].strip())
        )
    
    return render(request, 'clinic/patient_list.html', {'patients': patients})

def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')  # MySQL format
            
            create_record(
                'Patient',
                [
                    'patient_name', 'insurance_info',
                    'emergency_contact', 'ehr_link', 'feedback_rating',
                    'registration_date', 'created_at', 'updated_at'
                ],
                [
                    cd['patient_name'],
                    cd['insurance_info'], cd['emergency_contact'],
                    cd['ehr_link'], cd['feedback_rating'],
                    cd['registration_date'], current_time, current_time
                ]
            )
            return redirect('patient_list')
    else:
        form = PatientForm()
    return render(request, 'clinic/patient_form.html', {'form': form})

def patient_update(request, pk):
    data = get_record('Patient', 'patient_id', pk)
    if not data:
        return redirect('patient_list')
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Patient',
                ['patient_name',  'insurance_info', 'emergency_contact', 'ehr_link', 'feedback_rating', 'registration_date'],
                [cd['patient_name'],  cd['insurance_info'], cd['emergency_contact'],
                cd['ehr_link'], cd['feedback_rating'], cd['registration_date']],
                'patient_id', pk
            )
            return redirect('patient_list')
    else:
        form = PatientForm(initial=data)
    return render(request, 'clinic/patient_form.html', {'form': form})

@login_required
def patient_detail(request, pk):
    """
    Raw‐SQL detail view for a Patient and their contacts.
    """
    # 1) Fetch patient record
    with connection.cursor() as cursor:
        cursor.execute(
            r"SELECT * FROM Patient WHERE patient_id = %s",
            [pk]
        )
        row = cursor.fetchone()
        if not row:
            return redirect('patient_list')
        cols = [col[0] for col in cursor.description]
        patient = dict(zip(cols, row))

    # 2) Fetch all contacts for this patient
    with connection.cursor() as cursor:
        cursor.execute(
            r'''SELECT phone_number, email, address
               FROM Patient_Contact
              WHERE patient_id = %s''',
            [pk]
        )
        contacts = [
            dict(zip(['phone_number','email','address'], r))
            for r in cursor.fetchall()
        ]

    return render(request, 'clinic/patient_detail.html', {
        'patient': patient,
        'contacts': contacts
    })

@permission_required('clinic.delete_patient')
def patient_delete(request, pk):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # Delete related contacts first
                cursor.execute("DELETE FROM Patient_Contact WHERE patient_id = %s", [pk])
                # Delete patient
                cursor.execute("DELETE FROM Patient WHERE patient_id = %s", [pk])
            return redirect('patient_list')
        except Exception as e:
            # Handle errors here
            return redirect('patient_list')
    
    # Get request will redirect to list
    return redirect('patient_list')

def patient_contact_manage(request, pk):
    # Get existing contact (there should always be one due to trigger)
    contacts = list_records('Patient_Contact', where='patient_id = %s', params=[pk])
    contact = contacts[0] if contacts else None

    if request.method == 'POST':
        form = PatientContactForm(request.POST)
        if form.is_valid():
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE Patient_Contact
                    SET phone_number = %s,
                        email = %s,
                        address = %s
                    WHERE patient_id = %s
                """, [
                    form.cleaned_data['phone_number'],
                    form.cleaned_data['email'],
                    form.cleaned_data['address'],
                    pk
                ])
            return redirect('patient_list')
    else:
        initial_data = {
            'phone_number': contact['phone_number'] if contact else '',
            'email': contact['email'] if contact else '',
            'address': contact['address'] if contact else ''
        }
        form = PatientContactForm(initial=initial_data)

    return render(request, 'clinic/patient_contact_form.html', {
        'form': form,
        'patient_id': pk
    })
    
# ---------------------------------------------------------------
# Appointment CRUD

logger = logging.getLogger(__name__)
@login_required
def appointment_list(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                a.appointment_id,
                p.patient_name,
                s.name AS staff_name,
                a.appointment_date,
                a.appointment_time,
                a.appointment_status,
                a.reason_for_visit
            FROM Appointment a
            JOIN Patient p ON a.patient_id = p.patient_id
            LEFT JOIN Staff_Details s ON a.staff_id = s.staff_id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """)
        cols = [col[0] for col in cursor.description]
        appointments = [dict(zip(cols, row)) for row in cursor.fetchall()]
    
    return render(request, 'clinic/appointment_list.html', {
        'appointments': appointments
    })

@login_required
@permission_required('clinic.add_appointment')
def appointment_create(request):
    patients = list_records('Patient')
    staff = list_records('Staff_Details', where="occupation = 'doctor'")
    
    if request.method == 'POST':
        try:
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            create_record(
                'Appointment',
                [
                    'patient_id', 'staff_id', 'appointment_date', 'appointment_time',
                    'appointment_status', 'booking_method', 'reschedule_count',  # Added
                    'reminder_sent', 'reason_for_visit', 'notes',                # Added
                    'created_at', 'updated_at'
                ],
                [
                    request.POST['patient_id'],
                    request.POST['staff_id'],
                    request.POST['appointment_date'],
                    request.POST['appointment_time'],
                    request.POST.get('appointment_status', 'Scheduled'),
                    request.POST.get('booking_method', 'Online'),
                    0,  # Initial reschedule_count
                    False,  # Initial reminder_sent
                    request.POST.get('reason_for_visit', ''),
                    request.POST.get('notes', ''),
                    current_time,
                    current_time
                ]
            )
            # -------------------------------- Sending mail
            # Fetch emails
            patient_id = request.POST['patient_id']
            staff_id   = request.POST['staff_id']

            # patient email
            p_contact = list_records(
                'Patient_Contact',
                where="patient_id = %s",
                params=[patient_id]
            )
            patient_email = p_contact[0]['email'] if p_contact else None

            # staff email
            s_contact = list_records(
                'Staff_Contact',
                where="staff_id = %s",
                params=[staff_id]
            )
            staff_email = s_contact[0]['email'] if s_contact else None

            # Build notification
            subject = f"Appointment Scheduled on {request.POST['appointment_date']}"
            message = (
                f"Dear {{name}},\n\n"
                f"Your appointment has been scheduled as follows:\n"
                f"  • Date: {request.POST['appointment_date']}\n"
                f"  • Time: {request.POST['appointment_time']}\n"
                f"  • Reason: {request.POST.get('reason_for_visit','')}\n\n"
                "If you need to reschedule, please log in to your account.\n\n"
                "— Your Clinic Team"
            )

            # Send to patient
            if patient_email:
                send_mail(
                    subject,
                    message.format(name='Patient'),
                    settings.DEFAULT_FROM_EMAIL,
                    [patient_email],
                    fail_silently=False
                )

            staff_name = next(
                    (s['name'] for s in staff if str(s['staff_id']) == request.POST['staff_id']),
                    ''
                )
            
            # Send to staff
            if staff_email:
                send_mail(
                    subject,
                    message.format(name=f"Dr. {staff_name}"),
                    settings.DEFAULT_FROM_EMAIL,
                    [staff_email],
                    fail_silently=False
                )
            # -------------------------------- Emails Sents

            return redirect('appointment_list')
        except Exception as e:
            error = f"Error creating appointment: {str(e)}"
    else:
        error = None
    
    return render(request, 'clinic/appointment_form.html', {
        'patients': patients,
        'staff_members': staff,
        'status_choices': [c[0] for c in Appointment.APPOINTMENT_STATUS],
        'method_choices': [c[0] for c in Appointment.BOOKING_METHOD],
        'error': error if 'error' in locals() else None
    })
    
@login_required
@permission_required('clinic.change_appointment', raise_exception=True)
def appointment_update(request, pk):
    appointment = get_record('Appointment', 'appointment_id', pk)
    patients    = list_records('Patient')
    staff       = list_records('Staff_Details', where="occupation = 'doctor'")
    
    if not appointment:
        return redirect('appointment_list')
    
    if request.method == 'POST':
        try:
            # 1) Update the record
            update_record(
                'Appointment',
                [
                    'patient_id', 'staff_id', 'appointment_date', 'appointment_time',
                    'appointment_status', 'booking_method', 'reschedule_count',
                    'reminder_sent', 'reason_for_visit', 'notes', 'updated_at'
                ],
                [
                    request.POST['patient_id'],
                    request.POST['staff_id'],
                    request.POST['appointment_date'],
                    request.POST['appointment_time'],
                    request.POST.get('appointment_status', appointment['appointment_status']),
                    request.POST.get('booking_method', appointment['booking_method']),
                    appointment.get('reschedule_count', 0),
                    appointment.get('reminder_sent', False),
                    request.POST.get('reason_for_visit', appointment['reason_for_visit']),
                    request.POST.get('notes', appointment['notes']),
                    timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                ],
                'appointment_id', pk
            )

            # 2) Fetch updated emails
            p_contact = list_records(
                'Patient_Contact',
                where="patient_id = %s",
                params=[request.POST['patient_id']]
            )
            s_contact = list_records(
                'Staff_Contact',
                where="staff_id = %s",
                params=[request.POST['staff_id']]
            )
            patient_email = p_contact[0]['email'] if p_contact else None
            staff_email   = s_contact[0]['email']   if s_contact else None

            # 3) Build notification
            subject = f"Appointment Updated: {request.POST['appointment_date']} at {request.POST['appointment_time']}"
            message = (
                "Dear {name},\n\n"
                "Your appointment has been updated with the following details:\n"
                f"  • Date: {request.POST['appointment_date']}\n"
                f"  • Time: {request.POST['appointment_time']}\n"
                f"  • Status: {request.POST.get('appointment_status')}\n"
                f"  • Reason: {request.POST.get('reason_for_visit','')}\n\n"
                "If you have any questions, please contact us.\n\n"
                "— Your Clinic Team"
            )

            # 4) Send to patient
            if patient_email:
                send_mail(
                    subject,
                    message.format(name='Patient'),
                    settings.DEFAULT_FROM_EMAIL,
                    [patient_email],
                    fail_silently=False,
                )

            # 5) Send to staff
            if staff_email:
                # find this staff’s name for personalization
                staff_name = next(
                    (s['name'] for s in staff if str(s['staff_id']) == request.POST['staff_id']),
                    ''
                )
                send_mail(
                    subject,
                    message.format(name=f"Dr. {staff_name}"),
                    settings.DEFAULT_FROM_EMAIL,
                    [staff_email],
                    fail_silently=False,
                )

            return redirect('appointment_list')

        except Exception as e:
            error = f"Error updating appointment: {str(e)}"
    else:
        error = None
    
    return render(request, 'clinic/appointment_form.html', {
        'appointment':    appointment,
        'patients':       patients,
        'staff_members':  staff,
        'status_choices': [c[0] for c in Appointment.APPOINTMENT_STATUS],
        'method_choices': [c[0] for c in Appointment.BOOKING_METHOD],
        'error':          error
    })# ------------------------------------------------------------------
# Healthcare Providers (StaffDetails) CRUD and Assignment

@login_required
@permission_required('clinic.view_staff', raise_exception=True)
def provider_list(request):
    providers = list_records('Staff_Details')
    return render(request, 'clinic/provider_list.html', {'providers': providers})

@login_required
@permission_required('clinic.add_staff', raise_exception=True)
def provider_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            staff_id = create_record(
                'Staff_Details',
                ['name', 'occupation', 'speciality'],
                [cd['name'], cd['occupation'], cd['speciality']]
            )
            return redirect('provider_list')
    else:
        form = StaffForm()
    return render(request, 'clinic/provider_form.html', {'form': form})

@login_required
@permission_required('clinic.change_staff', raise_exception=True)
def provider_update(request, pk):
    data = get_record('Staff_Details', 'staff_id', pk)
    if not data:
        return redirect('provider_list')
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            update_record(
                'Staff_Details',
                ['name', 'occupation', 'speciality'],
                [cd['name'], cd['occupation'], cd['speciality'] ],
                'staff_id', pk
            )
            return redirect('provider_list')
    else:
        form = StaffForm(initial=data)
    return render(request, 'clinic/provider_form.html', {'form': form})

@login_required
@permission_required('clinic.add_staffdetails', raise_exception=True)
def provider_detail(request, pk):
    staff = get_record('Staff_Details', 'staff_id', pk)
    if not staff:
        return redirect('provider_list')
    
    # Fetch contact info
    with connection.cursor() as cursor:
        cursor.execute("SELECT phone_number, email, address FROM Staff_Contact WHERE staff_id = %s", [pk])
        contact_row = cursor.fetchone()
        contact = dict(zip(['phone_number', 'email', 'address'], contact_row)) if contact_row else None
    
    # Fetch assigned patients if doctor
    assigned_patients = []
    if staff['occupation'] == 'doctor':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.patient_id, p.patient_name 
                FROM Patients_Assigned pa
                JOIN Patient p ON pa.patient_id = p.patient_id
                WHERE pa.staff_id = %s
            """, [pk])
            assigned_patients = [
                {'patient_id': row[0], 'patient_name': row[1]} for row in cursor.fetchall()
            ]
    
    return render(request, 'clinic/provider_detail.html', {
        'staff': staff,
        'contact': contact,
        'assigned_patients': assigned_patients
    })

@login_required
@permission_required('clinic.delete_staff')
def provider_delete(request, pk):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Staff_Contact WHERE staff_id = %s", [pk])
                cursor.execute("DELETE FROM Patients_Assigned WHERE staff_id = %s", [pk])
                cursor.execute("DELETE FROM Staff_Details WHERE staff_id = %s", [pk])
            return redirect('provider_list')
        except Exception as e:
            pass
    return redirect('provider_list')

@login_required
def provider_contact_manage(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT phone_number, email, address FROM Staff_Contact WHERE staff_id = %s", [pk])
        contact_row = cursor.fetchone()
        contact = dict(zip(['phone_number', 'email', 'address'], contact_row)) if contact_row else None

    if request.method == 'POST':
        form = StaffContactForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            address = form.cleaned_data['address']
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE Staff_Contact
                    SET phone_number = %s, email = %s, address = %s
                    WHERE staff_id = %s
                """, [phone, email, address, pk])
            return redirect('provider_detail', pk=pk)
    else:
        initial = {
            'phone_number': contact['phone_number'] if contact else '',
            'email': contact['email'] if contact else '',
            'address': contact['address'] if contact else ''
        }
        form = StaffContactForm(initial=initial)
    
    return render(request, 'clinic/provider_contact_form.html', {'form': form, 'staff_id': pk})

@login_required
@permission_required('clinic.assign_doctor')
def assign_doctor(request, staff_id):
    staff = get_record('Staff_Details', 'staff_id', staff_id)
    if not staff or staff.get('occupation') != 'doctor':
        return redirect('provider_list')
    
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        patient = get_record('Patient', 'patient_id', patient_id)
        if patient:
            with connection.cursor() as cursor:
                # Remove existing assignment for patient
                cursor.execute("DELETE FROM Patients_Assigned WHERE patient_id = %s", [patient_id])
                # Assign new doctor
                cursor.execute("""
                    INSERT INTO Patients_Assigned (staff_id, patient_id, assigned_date)
                    VALUES (%s, %s, %s)
                """, [staff_id, patient_id, timezone.now().date()])
            return redirect('provider_detail', pk=staff_id)
    
    # Fetch all patients
    patients = list_records('Patient')
    return render(request, 'clinic/assign_doctor.html', {
        'staff': staff,
        'patients': patients
    })

# ------------------------------------------------------------------------------
# Drug Management
def drug_list(request):
    drugs = list_records('Drug')
    return render(request, 'clinic/drug_list.html', {'drugs': drugs})

def drug_create(request):
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Remove manual timestamp handling
            create_record(
                'Drug',
                ['drug_name','drug_type','description','dosage_form','strength',
                 'manufacturer','interactions','contraindications','side_effects','warnings'],
                [cd['drug_name'], cd['drug_type'], cd['description'], cd['dosage_form'],
                 cd['strength'], cd['manufacturer'], cd['interactions'],
                 cd['contraindications'], cd['side_effects'], cd['warnings']]
            )
            return redirect('drug_list')
    else:
        form = DrugForm()
    return render(request, 'clinic/drug_form.html', {'form': form})


def drug_detail(request, pk):
    drug = get_record('Drug', 'drug_id', pk)
    return render(request, 'clinic/drug_detail.html', {'drug': drug})

def drug_update(request, pk):
    data = get_record('Drug', 'drug_id', pk)
    if not data:
        return redirect('drug_list')
    
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Drug',
                ['drug_name','drug_type','description','dosage_form','strength',
                 'manufacturer','interactions','contraindications','side_effects','warnings'],
                [cd['drug_name'], cd['drug_type'], cd['description'], cd['dosage_form'],
                 cd['strength'], cd['manufacturer'], cd['interactions'],
                 cd['contraindications'], cd['side_effects'], cd['warnings']],
                'drug_id', pk
            )
            return redirect('drug_detail', pk=pk)
    else:
        form = DrugForm(initial=data)
    return render(request, 'clinic/drug_form.html', {'form': form})

def drug_delete(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Drug WHERE drug_id = %s", [pk])
        return redirect('drug_list')
    return render(request, 'clinic/confirm_delete.html', {'object': 'Drug'})


# -----------------------------------------------------------------
# Prescription
def prescription_list(request):
    pres = list_records('Prescription')
    return render(request, 'clinic/prescription_list.html', {'prescriptions': pres})
def prescription_detail(request, pk):
    prescription = get_record('Prescription', 'prescription_id', pk)
    if not prescription:
        raise Http404("Prescription not found")

    # get related drugs
    drugs = list_records(
        'Prescription_Drug',
        where='prescription_id = %s',
        params=[pk]
    )
    # enrich drug info
    drug_ids = []
    for d in drugs:
        info = get_record('Drug', 'drug_id', d['drug_id'])
        d['drug_name'] = info.get('drug_name', '')
        d['warnings'] = info.get('warnings', '')
        drug_ids.append(d['drug_id'])

    # check pairwise interactions if more than one drug
    interactions = []
    if len(drug_ids) > 1:
        interactions = check_interactions_for_drugs(drug_ids)

    return render(request, 'clinic/prescription_detail.html', {
        'prescription': prescription,
        'prescription_drugs': drugs,
        'interactions': interactions,
    })


def prescription_create(request):
    all_drugs = list_records('Drug')
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            new_id = create_record(
                'Prescription',
                [
                    'patient_id','staff_id','diagnoses','treatments','allergies',
                    'laboratory_test_results','imaging_studies','dosage_instruction',
                    'refill_requests','notes','alert'
                ],
                [
                    cd['patient'].patient_id,
                    cd['staff'].staff_id,
                    cd['diagnoses'],
                    cd['treatments'],
                    cd['allergies'],
                    cd['laboratory_test_results'],
                    cd['imaging_studies'],
                    cd['dosage_instruction'],
                    cd['refill_requests'],
                    cd['notes'],
                    cd.get('alert','')
                ]
            )
            # insert drugs
            for drug_id, qty, instr in zip(
                request.POST.getlist('drug_id'),
                request.POST.getlist('quantity'),
                request.POST.getlist('instructions')
            ):
                create_record(
                    'Prescription_Drug',
                    ['prescription_id','drug_id','quantity','instructions'],
                    [new_id, drug_id, qty, instr]
                )
            messages.success(request, 'Prescription created successfully!')
            return redirect('prescription_detail', pk=new_id)
        messages.error(request, 'Please correct the errors below')
    else:
        form = PrescriptionForm()

    return render(request, 'clinic/prescription_form.html', {
        'form': form,
        'all_drugs': all_drugs,
        'existing_drugs': [],
        'is_update': False,
    })


def prescription_update(request, pk):
    existing = get_record('Prescription', 'prescription_id', pk)
    if not existing:
        raise Http404("Prescription not found")

    all_drugs = list_records('Drug')
    existing_drugs = list_records(
        'Prescription_Drug',
        where='prescription_id = %s',
        params=[pk]
    )

    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Prescription',
                [
                    'patient_id','staff_id','diagnoses','treatments','allergies',
                    'laboratory_test_results','imaging_studies','dosage_instruction',
                    'refill_requests','notes','alert'
                ],
                [
                    cd['patient'].patient_id,
                    cd['staff'].staff_id,
                    cd['diagnoses'],
                    cd['treatments'],
                    cd['allergies'],
                    cd['laboratory_test_results'],
                    cd['imaging_studies'],
                    cd['dosage_instruction'],
                    cd['refill_requests'],
                    cd['notes'],
                    cd.get('alert','')
                ],
                'prescription_id',
                pk
            )
            # replace drug rows
            with connection.cursor() as c:
                c.execute("DELETE FROM Prescription_Drug WHERE prescription_id = %s", [pk])
            for drug_id, qty, instr in zip(
                request.POST.getlist('drug_id'),
                request.POST.getlist('quantity'),
                request.POST.getlist('instructions')
            ):
                create_record(
                    'Prescription_Drug',
                    ['prescription_id','drug_id','quantity','instructions'],
                    [pk, drug_id, qty, instr]
                )
            messages.success(request, 'Prescription updated!')
            return redirect('prescription_detail', pk=pk)
    else:
        form = PrescriptionForm(initial={
            'patient': existing['patient_id'],
            'staff': existing['staff_id'],
            'diagnoses': existing['diagnoses'],
            'treatments': existing['treatments'],
            'allergies': existing['allergies'],
            'laboratory_test_results': existing['laboratory_test_results'],
            'imaging_studies': existing['imaging_studies'],
            'dosage_instruction': existing['dosage_instruction'],
            'refill_requests': existing['refill_requests'],
            'notes': existing['notes'],
            'alert': existing['alert'],
        })

    return render(request, 'clinic/prescription_form.html', {
        'form': form,
        'all_drugs': all_drugs,
        'existing_drugs': existing_drugs,
        'is_update': True,
    })
    
def prescription_delete(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            # First delete related PrescriptionDrug entries
            cursor.execute(
                "DELETE FROM Prescription_Drug WHERE prescription_id = %s",
                [pk]
            )
            # Then delete the prescription
            cursor.execute(
                "DELETE FROM Prescription WHERE prescription_id = %s",
                [pk]
            )
        return redirect('prescription_list')
    return render(request, 'clinic/confirm_delete.html', {'object': 'Prescription'})

def prescription_drugs(request, prescription_id):
    # Get prescription using your existing get_record function
    prescription = get_record('Prescription', 'prescription_id', prescription_id)
    if not prescription:
        return redirect('prescription_list')

    # Get related drugs using the PrescriptionDrug model
    PrescriptionDrugFormSet = inlineformset_factory(
        Prescription, 
        PrescriptionDrug, 
        form=PrescriptionDrugForm, 
        extra=1,
        can_delete=True
    )

    if request.method == 'POST':
        formset = PrescriptionDrugFormSet(
            request.POST, 
            instance=Prescription.objects.get(pk=prescription_id)
        )
        
        if formset.is_valid():
            # Check for drug interactions
            drug_ids = [form.cleaned_data['drug'].drug_id for form in formset if form.cleaned_data and not form.cleaned_data.get('DELETE', False)]
            interactions = check_interactions_for_drugs(drug_ids)
            
            if interactions:
                # Store temporary data in session
                request.session['temp_drug_data'] = {
                    'form_data': request.POST,
                    'interactions': interactions,
                    'prescription_id': prescription_id
                }
                return redirect('confirm_interactions')
            
            formset.save()
            return redirect('prescription_detail', pk=prescription_id)

    else:
        formset = PrescriptionDrugFormSet(
            instance=Prescription.objects.get(pk=prescription_id)
        )

    return render(request, 'clinic/prescription_drugs.html', {
        'formset': formset,
        'prescription': prescription
    })
# --------------------------------------------------------------------------
# Drug Interaction Check
def check_interactions(request):
    drug_ids = request.GET.getlist('drug_ids[]')
    interactions = check_interactions_for_drugs([int(id) for id in drug_ids])
    return JsonResponse({'interactions': interactions})

def confirm_interactions(request):
    if request.method == 'POST':
        temp_data = request.session.get('temp_prescription_data')
        if temp_data:
            form = PrescriptionForm(temp_data['form_data'])
            formset = PrescriptionDrugFormSet(temp_data['form_data'], prefix='drugs')
            
            if form.is_valid() and formset.is_valid():
                prescription = form.save(commit=False)
                prescription.alert = "\n".join(
                    [f"Interaction between {i['drug1']} and {i['drug2']}: {i['details']}" 
                     for i in temp_data['interactions']]
                )
                prescription.save()
                formset.instance = prescription
                formset.save()
                del request.session['temp_prescription_data']
                return redirect('prescription_detail', pk=prescription.pk)
        
    temp_data = request.session.get('temp_prescription_data', {})
    return render(request, 'clinic/interaction_confirm.html', {
        'interactions': temp_data.get('interactions', [])
    })
def drug_interaction_create(request):
    if request.method == 'POST':
        form = DrugInteractionForm(request.POST)
        if form.is_valid():
            try:
                interaction = form.save()
                messages.success(request, 'Drug interaction added successfully!')
                return redirect('drug_list')
            except Exception as e:
                messages.error(request, f'Error saving interaction: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = DrugInteractionForm()
    
    return render(request, 'clinic/interaction_form.html', {'form': form})

def drug_interaction_list(request):
    all_drugs = Drug.objects.all().order_by('drug_name')
    interactions = DrugInteraction.objects.all().select_related('drug_1', 'drug_2')
    
    # Create a dictionary for quick lookup
    interaction_map = {}
    for interaction in interactions:
        key = tuple(sorted([interaction.drug_1_id, interaction.drug_2_id]))
        interaction_map[key] = interaction
    
    # Generate unique pairs
    drug_pairs = []
    seen = set()
    for interaction in interactions:
        pair = tuple(sorted([interaction.drug_1_id, interaction.drug_2_id]))
        if pair not in seen:
            seen.add(pair)
            drug_pairs.append({
                'drug1': interaction.drug_1,
                'drug2': interaction.drug_2,
                'interaction': interaction,
                'is_default': interaction.is_default()
            })
    
    # Sort by drug names
    drug_pairs.sort(key=lambda x: (x['drug1'].drug_name, x['drug2'].drug_name))
    
    paginator = Paginator(drug_pairs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'clinic/drug_interaction_list.html', {
        'page_obj': page_obj
    })

def drug_interaction_edit(request, drug1_id, drug2_id):
    try:
        drug1 = Drug.objects.get(pk=drug1_id)
        drug2 = Drug.objects.get(pk=drug2_id)
    except Drug.DoesNotExist:
        return redirect('drug_interaction_list')

    # Find existing interaction in any direction
    interaction = DrugInteraction.objects.filter(
        (Q(drug_1=drug1, drug_2=drug2) | 
         Q(drug_1=drug2, drug_2=drug1))
    ).first()

    if request.method == 'POST':
        form = DrugInteractionForm(request.POST, instance=interaction)
        if form.is_valid():
            # Ensure consistent ordering of drug pairs
            cleaned_data = form.cleaned_data
            drug_a, drug_b = sorted([cleaned_data['drug_1'], cleaned_data['drug_2']], 
                                   key=lambda x: x.drug_name)
            
            # Update instance with ordered drugs
            interaction = form.save(commit=False)
            interaction.drug_1 = drug_a
            interaction.drug_2 = drug_b
            interaction.save()
            
            messages.success(request, 'Interaction updated successfully!')
            return redirect('drug_interaction_list')
    else:
        initial = {
            'drug_1': drug1,
            'drug_2': drug2,
            'interaction_details': interaction.interaction_details if interaction else '',
            'severity_level': interaction.severity_level if interaction else 'Low',
            'alert': interaction.alert if interaction else ''
        }
        form = DrugInteractionForm(instance=interaction, initial=initial)
    
    return render(request, 'clinic/drug_interaction_edit.html', {
        'form': form,
        'drug1': drug1,
        'drug2': drug2
    })

# --------------------------------------------------------------
# Insurance Management
def insurance_list(request):
    ins = list_records('Insurance')
    return render(request, 'clinic/insurance_list.html', {'insurances': ins})

def insurance_create(request):
    if request.method == 'POST':
        form = InsuranceForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            create_record(
                'Insurance',
                ['provider_name','policy_number','treatment_coverage_details','amount_covered'],
                [cd['provider_name'], cd['policy_number'], cd['treatment_coverage_details'], cd['amount_covered']]
            )
            return redirect('insurance_list')
    else:
        form = InsuranceForm()
    return render(request, 'clinic/insurance_form.html', {'form': form})

def insurance_detail(request, pk):
    insurance = get_record('Insurance', 'insurance_id', pk)
    return render(request, 'clinic/insurance_detail.html', {'insurance': insurance})

def insurance_update(request, pk):
    data = get_record('Insurance', 'insurance_id', pk)
    if request.method == 'POST':
        form = InsuranceForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Insurance',
                ['provider_name','policy_number','treatment_coverage_details','amount_covered'],
                [cd['provider_name'], cd['policy_number'], 
                 cd['treatment_coverage_details'], cd['amount_covered']],
                'insurance_id', pk
            )
            return redirect('insurance_detail', pk=pk)
    else:
        form = InsuranceForm(initial=data)
    return render(request, 'clinic/insurance_form.html', {'form': form})

def insurance_delete(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Insurance WHERE insurance_id = %s", [pk])
        return redirect('insurance_list')
    return render(request, 'clinic/confirm_delete.html', {'object': 'Insurance'})

# --------------------------------------------------------------------------
# Billing
def billing_create(request):
    if request.method == 'POST':
        form = BillingForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            create_record(
                'Billing',
                ['patient_id','insurance_id','total_amount','payment_status','billing_date'],
                [cd['patient'].patient_id, cd['insurance'].insurance_id,
                 cd['total_amount'], cd['payment_status'], cd['billing_date']]
            )
            return redirect('billing_list')
    else:
        form = BillingForm()
    return render(request, 'clinic/billing_form.html', {'form': form})

# Billing Management
def billing_list(request):
    raw = list_records('Billing')
    bills = []
    for b in raw:
        # get patient name
        p = get_record('Patient', 'patient_id', b['patient_id'])
        b['patient_name'] = p.get('patient_name', '') if p else ''
        # get insurance name
        if b.get('insurance_id'):
            i = get_record('Insurance', 'insurance_id', b['insurance_id'])
            b['insurance_name'] = i.get('provider_name', '') if i else ''
        else:
            b['insurance_name'] = None
        bills.append(b)

    return render(request, 'clinic/billing_list.html', {
        'bills': bills
    })


def billing_detail(request, pk):
    # 1) fetch the raw billing row
    bill = get_record('Billing', 'billing_id', pk)
    if not bill:
        raise Http404("Bill not found")

    # 2) look up the patient name
    patient = get_record('Patient', 'patient_id', bill['patient_id'])
    bill['patient_name'] = patient.get('patient_name', '') if patient else ''

    # 3) look up the insurance provider name (if any)
    ins_id = bill.get('insurance_id')
    if ins_id:
        ins = get_record('Insurance', 'insurance_id', ins_id)
        bill['insurance_name'] = ins.get('provider_name', '') if ins else ''
    else:
        bill['insurance_name'] = None

    return render(request, 'clinic/billing_detail.html', {
        'bill': bill
    })

def billing_update(request, pk):
    data = get_record('Billing', 'billing_id', pk)
    if request.method == 'POST':
        form = BillingForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Billing',
                ['patient_id','insurance_id','total_amount','payment_status','billing_date'],
                [cd['patient'].patient_id, cd['insurance'].insurance_id if cd['insurance'] else None,
                 cd['total_amount'], cd['payment_status'], cd['billing_date']],
                'billing_id', pk
            )
            return redirect('billing_detail', pk=pk)
    else:
        # Convert IDs to model instances
        from .models import Patient, Insurance
        data['patient'] = Patient.objects.get(pk=data['patient_id'])
        data['insurance'] = Insurance.objects.get(pk=data['insurance_id']) if data['insurance_id'] else None
        form = BillingForm(initial=data)
    return render(request, 'clinic/billing_form.html', {'form': form})

def billing_delete(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Billing WHERE billing_id = %s", [pk])
        return redirect('billing_list')
    return render(request, 'clinic/confirm_delete.html', {'object': 'Billing'})

# -------------------------------------------------------------------------------
# Reporting

def report_list(request):
    reports = list_records('Report')
    return render(request, 'clinic/report_list.html', {'reports': reports})

def report_create(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            cd = form.cleaned_data
            create_record(
                'Report',
                ['patient_id','billing_id','insurance_id','created_at','updated_at'],
                [cd['patient'].patient_id, cd['billing'].billing_id,
                 cd['insurance'].insurance_id if cd['insurance'] else None,current_time,current_time]
            )
            return redirect('report_list')
    else:
        form = ReportForm()
    return render(request, 'clinic/report_form.html', {'form': form})

def report_detail(request, pk):
    report = get_record('Report', 'report_id', pk)
    return render(request, 'clinic/report_detail.html', {'report': report})

def report_update(request, pk):
    data = get_record('Report', 'report_id', pk)
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            update_record(
                'Report',
                ['patient_id','billing_id','insurance_id','updated_at'],
                [cd['patient'].patient_id, cd['billing'].billing_id,
                 cd['insurance'].insurance_id if cd['insurance'] else None, current_time],
                'report_id', pk
            )
            return redirect('report_detail', pk=pk)
    else:
        from .models import Patient, Billing, Insurance
        data['patient'] = Patient.objects.get(pk=data['patient_id'])
        data['billing'] = Billing.objects.get(pk=data['billing_id'])
        data['insurance'] = Insurance.objects.get(pk=data['insurance_id']) if data['insurance_id'] else None
        form = ReportForm(initial=data)
    return render(request, 'clinic/report_form.html', {'form': form})

def report_delete(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Report WHERE report_id = %s", [pk])
        return redirect('report_list')
    return render(request, 'clinic/confirm_delete.html', {'object': 'Report'})

# ------------------------------------------------
# EHR
def ehr_detail(request, pk):
    with connection.cursor() as cursor:
        # Get comprehensive patient health record
        cursor.execute("""
            SELECT p.*, 
                   GROUP_CONCAT(pr.diagnoses) AS diagnoses,
                   GROUP_CONCAT(pr.treatments) AS treatments,
                   GROUP_CONCAT(d.drug_name) AS medications
            FROM Patient p
            LEFT JOIN Prescription pr ON p.patient_id = pr.patient_id
            LEFT JOIN PrescriptionDrug pd ON pr.prescription_id = pd.prescription_id
            LEFT JOIN Drug d ON pd.drug_id = d.drug_id
            WHERE p.patient_id = %s
            GROUP BY p.patient_id
        """, [pk])
        ehr = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
    
    return render(request, 'clinic/ehr_detail.html', {'ehr': ehr})

# ---------------------------------------------------------------------
# User Authentication: SIGNUP, LOGIN & LOGOUT

def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email    = request.POST['email']
        raw_pw   = request.POST['password']
        hashed   = make_password(raw_pw)
        try:
            with connection.cursor() as cursor:
                # 1) Insert into auth_user, including first_name & last_name as empty strings
                cursor.execute(r"""
                    INSERT INTO auth_user
                    (username, password, email, first_name, last_name,
                    is_active, is_staff, is_superuser,
                    date_joined, last_login)
                    VALUES
                    (%s, %s, %s, %s, %s,
                    1, 0, 0,
                    NOW(), NOW())
                """, [
                    username,
                    hashed,
                    email,
                    '',        # first_name
                    ''         # last_name
                ])
                user_id = cursor.lastrowid

                # 2) Assign to Patient group by default
                cursor.execute(r"""
                    SELECT id FROM auth_group WHERE name = %s
                """, ['Patient'])
                grp = cursor.fetchone()
                if grp:
                    cursor.execute(r"""
                        INSERT INTO auth_user_groups (user_id, group_id)
                        VALUES (%s, %s)
                    """, [user_id, grp[0]])
        except IntegrityError as e:
            return render(request, 'clinic/signup.html', {'error': 'Username already exists.'})
        # 3) Authenticate & log in via Django’s auth system
        user = authenticate(request, username=username, password=raw_pw)
        if user:
            login(request, user)
            return redirect('home')
            
    return render(request, 'clinic/signup.html')


def login_view(request):
    error = None
    if request.method == 'POST':
        un = request.POST['username']
        pw = request.POST['password']
        user = authenticate(request, username=un, password=pw)
        if user:
            login(request, user)
            return redirect('home')
        else:
            error = "Invalid username or password."
    return render(request, 'clinic/login.html', {'error': error})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')