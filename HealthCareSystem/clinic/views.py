# clinic/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from .forms import (
    PatientForm, AppointmentForm, StaffForm, InsuranceForm,
    BillingForm, PrescriptionForm, DrugForm, ReportForm, PatientContactForm
)
from .db_utils import (
    list_records, get_record, create_record, update_record
)
import logging
from django.utils import timezone

# user authentication imports
from django.db import connection, IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect

# 1) Home / Static pages
#
class HomeView(TemplateView):
    template_name = "clinic/home.html"

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


# Patient Management Views
def patient_list(request):
    patients = list_records('Patient')
    
    # Check contact status for each patient
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
        # 1) Fetch *all* rows from Appointment
        cursor.execute("SELECT * FROM Appointment")
        raw_rows = cursor.fetchall()
        raw_cols = [col[0] for col in cursor.description]
        raw_appointments = [dict(zip(raw_cols, row)) for row in raw_rows]
        logger.debug(f"RAW Appointment rows: {raw_appointments}")

        # 2) Try the JOIN query
        cursor.execute("""
            SELECT
              a.appointment_id,
              a.appointment_date,
              a.appointment_time,
              a.appointment_status AS patient_demographics
            FROM Appointment a
            JOIN Patient p ON a.patient_id = p.patient_id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """)
        join_cols = [col[0] for col in cursor.description]
        joined = [dict(zip(join_cols, row)) for row in cursor.fetchall()]
        logger.debug(f"JOINed Appointment rows: {joined}")

    # Pass both to the template
    return render(request, 'clinic/appointment_list.html', {
        'appointments': joined,
        'raw_appointments': raw_appointments,
    })

@login_required
@permission_required('clinic.add_appointment', raise_exception=True)
def appointment_create(request):
    error = None
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Extract IDs safely
            patient_id = cd['patient'].patient_id
            staff_id   = cd['staff'].staff_id
            current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                create_record(
                    'Appointment',
                    [
                        'patient_id', 'staff_id', 'appointment_date', 'appointment_time',
                        'appointment_status', 'created_at', 'updated_at'
                    ],
                    [
                        patient_id, staff_id, cd['appointment_date'],
                        cd['appointment_time'], cd['appointment_status'],
                        current_time, current_time
                    ]
                )
                return redirect('appointment_list')

            except IntegrityError as e:
                # Likely the staff_id does not exist
                form.add_error('staff', "Invalid staff selected. Please choose an existing provider.")

    else:
        form = AppointmentForm()

    return render(request, 'clinic/appointment_form.html', {
        'form': form,
        'error': error
    })


@login_required
def appointment_update(request, pk):
    data = get_record('Appointment', 'appointment_id', pk)
    if not data:
        return redirect('appointment_list')

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            patient_id = cd['patient'].patient_id
            staff_id   = cd['staff'].staff_id

            try:
                update_record(
                    'Appointment',
                    [
                        'patient_id','staff_id','appointment_date','appointment_time',
                        'appointment_status','reschedule_count','booking_method',
                        'reminder_sent','reason_for_visit','notes'
                    ],
                    [
                        patient_id, staff_id, cd['appointment_date'],
                        cd['appointment_time'], cd['appointment_status'],
                        data['reschedule_count'],
                        cd['booking_method'],
                        data['reminder_sent'],
                        cd['reason_for_visit'], cd['notes']
                    ],
                    'appointment_id', pk
                )
                return redirect('appointment_list')

            except IntegrityError:
                form.add_error('staff', "Invalid staff selected. Please choose an existing provider.")

    else:
        # Prepare initial data for the form
        from .models import Patient, StaffDetails
        data['patient'] = Patient.objects.get(pk=data['patient_id'])
        data['staff']   = StaffDetails.objects.get(pk=data['staff_id'])
        form = AppointmentForm(initial=data)

    return render(request, 'clinic/appointment_form.html', {
        'form': form
    })

# Healthcare Providers (StaffDetails)

def provider_list(request):
    providers = list_records('Staff_Details')
    return render(request, 'clinic/providers.html', {'providers': providers})

def provider_create(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            create_record(
                'Staff_Details',
                ['name','occupation','speciality'],
                [cd['name'], cd['occupation'], cd['speciality']]
            )
            return redirect('providers')
    else:
        form = StaffForm()
    return render(request, 'clinic/provider_form.html', {'form': form})

def provider_update(request, pk):
    data = get_record('Staff_Details', 'staff_id', pk)
    if not data:
        return redirect('providers')
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Staff_Details',
                ['name','occupation','speciality'],
                [cd['name'], cd['occupation'], cd['speciality']],
                'staff_id', pk
            )
            return redirect('providers')
    else:
        form = StaffForm(initial=data)
    return render(request, 'clinic/provider_form.html', {'form': form})


#
# 5) Billing & 6) Insurance
#
def insurance_list(request):
    ins = list_records('Insurance')
    return render(request, 'clinic/billing.html', {'insurances': ins})

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
            return redirect('billing')
    else:
        form = InsuranceForm()
    return render(request, 'clinic/insurance_form.html', {'form': form})

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
            return redirect('billing')
    else:
        form = BillingForm()
    return render(request, 'clinic/billing_form.html', {'form': form})


#
# 7) Prescription & 8) Drug Management
#
def prescription_list(request):
    pres = list_records('Prescription')
    return render(request, 'clinic/medication.html', {'prescriptions': pres})

def prescription_create(request):
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            create_record(
                'Prescription',
                ['patient_id','staff_id','diagnoses','treatments','allergies',
                 'laboratory_test_results','imaging_studies','dosage_instruction',
                 'refill_requests','notes','alert'],
                [cd['patient'].patient_id, cd['staff'].staff_id, cd['diagnoses'],
                 cd['treatments'], cd['allergies'], cd['laboratory_test_results'],
                 cd['imaging_studies'], cd['dosage_instruction'], cd['refill_requests'],
                 cd['notes'], cd['alert']]
            )
            return redirect('medication')
    else:
        form = PrescriptionForm()
    return render(request, 'clinic/prescription_form.html', {'form': form})

def drug_list(request):
    drugs = list_records('Drug')
    return render(request, 'clinic/medication.html', {'drugs': drugs})

def drug_create(request):
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            create_record(
                'Drug',
                ['drug_name','drug_type','description','dosage_form','strength',
                 'manufacturer','interactions','contraindications','side_effects','warnings'],
                [cd['drug_name'], cd['drug_type'], cd['description'], cd['dosage_form'],
                 cd['strength'], cd['manufacturer'], cd['interactions'],
                 cd['contraindications'], cd['side_effects'], cd['warnings']]
            )
            return redirect('medication')
    else:
        form = DrugForm()
    return render(request, 'clinic/drug_form.html', {'form': form})


#
# 9) Reporting
#
def report_list(request):
    reports = list_records('Report')
    return render(request, 'clinic/reporting.html', {'reports': reports})

def report_create(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            create_record(
                'Report',
                ['patient_id','billing_id','insurance_id'],
                [cd['patient'].patient_id, cd['billing'].billing_id,
                 cd['insurance'].insurance_id if cd['insurance'] else None]
            )
            return redirect('reporting')
    else:
        form = ReportForm()
    return render(request, 'clinic/report_form.html', {'form': form})

# Drug Management
def drug_list(request):
    drugs = list_records('Drug')
    return render(request, 'clinic/drug_list.html', {'drugs': drugs})

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

# Similar pattern for Insurance, Billing, Prescription, Report
# -----------------------------------------------------------

# Insurance Management
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

# Billing Management
def billing_list(request):
    bills = list_records('Billing')
    return render(request, 'clinic/billing_list.html', {'bills': bills})

def billing_detail(request, pk):
    bill = get_record('Billing', 'billing_id', pk)
    return render(request, 'clinic/billing_detail.html', {'bill': bill})

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

# Prescription Management
def prescription_detail(request, pk):
    prescription = get_record('Prescription', 'prescription_id', pk)
    return render(request, 'clinic/prescription_detail.html', {'prescription': prescription})

def prescription_update(request, pk):
    data = get_record('Prescription', 'prescription_id', pk)
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Prescription',
                ['patient_id','staff_id','diagnoses','treatments','allergies',
                 'laboratory_test_results','imaging_studies','dosage_instruction',
                 'refill_requests','notes','alert'],
                [cd['patient'].patient_id, cd['staff'].staff_id, cd['diagnoses'],
                 cd['treatments'], cd['allergies'], cd['laboratory_test_results'],
                 cd['imaging_studies'], cd['dosage_instruction'], cd['refill_requests'],
                 cd['notes'], cd['alert']],
                'prescription_id', pk
            )
            return redirect('prescription_detail', pk=pk)
    else:
        from .models import Patient, StaffDetails
        data['patient'] = Patient.objects.get(pk=data['patient_id'])
        data['staff'] = StaffDetails.objects.get(pk=data['staff_id'])
        form = PrescriptionForm(initial=data)
    return render(request, 'clinic/prescription_form.html', {'form': form})

def prescription_delete(request, pk):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Prescription WHERE prescription_id = %s", [pk])
        return redirect('prescription_list')
    return render(request, 'clinic/confirm_delete.html', {'object': 'Prescription'})

# Report Management
def report_detail(request, pk):
    report = get_record('Report', 'report_id', pk)
    return render(request, 'clinic/report_detail.html', {'report': report})

def report_update(request, pk):
    data = get_record('Report', 'report_id', pk)
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            update_record(
                'Report',
                ['patient_id','billing_id','insurance_id'],
                [cd['patient'].patient_id, cd['billing'].billing_id,
                 cd['insurance'].insurance_id if cd['insurance'] else None],
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