from django.db import models

class Patient(models.Model):
    patient_id = models.AutoField(primary_key=True)
    patient_name = models.CharField(max_length=255)
    insurance_info = models.CharField(max_length=255)
    emergency_contact = models.CharField(max_length=10)  # use CharField for fixed length
    ehr_link = models.CharField(max_length=255)
    feedback_rating = models.PositiveSmallIntegerField()  # you can add validators below
    registration_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Patient {self.patient_id}: {self.patient_name}"
    class Meta:
        db_table = 'Patient'


class PatientContact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='contacts')
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=255)
    address = models.TextField()

    def __str__(self):
        return f"Contact for Patient {self.patient.patient_id}"
    class Meta:
        db_table = 'Patient_Contact'

class StaffDetails(models.Model):
    staff_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    occupation = models.CharField(max_length=255, blank=True, null=True)
    speciality = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return self.name
    class Meta:
        db_table = 'Staff_Details'


class StaffContact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(StaffDetails, on_delete=models.CASCADE, related_name='contacts')
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=255)
    address = models.TextField()
    def __str__(self):
        return f"Contact for Staff {self.staff.name}"
    class Meta:
        db_table = 'Staff_Contact'


class PatientsAssigned(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(StaffDetails, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    assigned_date = models.DateField(auto_now_add=True)
    def __str__(self):
        return f"{self.staff.name} assigned to Patient {self.patient.patient_id}"
    class Meta:
        db_table = 'Patients_Assigned'

class Insurance(models.Model):
    insurance_id = models.AutoField(primary_key=True)
    provider_name = models.CharField(max_length=255)
    policy_number = models.CharField(max_length=255, unique=True)
    treatment_coverage_details = models.TextField()
    amount_covered = models.DecimalField(max_digits=15, decimal_places=2)
    def __str__(self):
        return self.provider_name
    class Meta:
        db_table = 'Insurance'


class Billing(models.Model):
    PAYMENT_STATUS = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Denied', 'Denied'),
    )
    billing_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    insurance = models.ForeignKey(Insurance, on_delete=models.SET_NULL, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='Pending')
    billing_date = models.DateField()
    def __str__(self):
        return f"Billing {self.billing_id} for Patient {self.patient.patient_id}"
    class Meta:
        db_table = 'Billing'


class Prescription(models.Model):
    prescription_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    staff = models.ForeignKey(StaffDetails, on_delete=models.CASCADE)
    diagnoses = models.CharField(max_length=255, blank=True, null=True)
    treatments = models.CharField(max_length=255, blank=True, null=True)
    allergies = models.CharField(max_length=255, blank=True, null=True)
    laboratory_test_results = models.TextField(blank=True, null=True)
    imaging_studies = models.TextField(blank=True, null=True)
    dosage_instruction = models.TextField(blank=True, null=True)
    refill_requests = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    alert = models.TextField(default='No alert')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Prescription {self.prescription_id}"
    class Meta:
        db_table = 'Prescription'


class Drug(models.Model):
    drug_id = models.AutoField(primary_key=True)
    drug_name = models.CharField(max_length=255)
    drug_type = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    dosage_form = models.CharField(max_length=255, blank=True, null=True)
    strength = models.CharField(max_length=100, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    interactions = models.TextField(blank=True, null=True)
    contraindications = models.TextField(blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    warnings = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.drug_name
    class Meta:
        db_table = 'Drug'


class PrescriptionDrug(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    instructions = models.TextField()
    def __str__(self):
        return f"Prescription {self.prescription.prescription_id} - Drug {self.drug.drug_name}"
    class Meta:
        unique_together = ('prescription', 'drug')
        db_table = 'Prescription_Drug'


class DrugInteraction(models.Model):
    drug_id_1 = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='drug1')
    drug_id_2 = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='drug2')
    interaction_details = models.CharField(max_length=500)
    severity_level = models.CharField(max_length=10, choices=(('Low','Low'),('Moderate','Moderate'),('High','High')))
    alert = models.TextField()
    def __str__(self):
        return f"Interaction between {self.drug_id_1.drug_name} and {self.drug_id_2.drug_name}"
    class Meta:
        unique_together = ('drug_id_1', 'drug_id_2')
        db_table = 'Drug_Interaction'


class Appointment(models.Model):
    APPOINTMENT_STATUS = (
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('No-show', 'No-show'),
    )
    BOOKING_METHOD = (
        ('Online', 'Online'),
        ('Offline', 'Offline'),
        ('Mobile App', 'Mobile App'),
    )
    appointment_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    # We set null=True for staff so that if a staff member is removed, appointments are not deleted.
    staff = models.ForeignKey(StaffDetails, on_delete=models.SET_NULL, null=True, blank=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_status = models.CharField(max_length=10, choices=APPOINTMENT_STATUS, default='Scheduled')
    reschedule_count = models.IntegerField(default=0)
    booking_method = models.CharField(max_length=10, choices=BOOKING_METHOD, default='Online')
    reminder_sent = models.BooleanField(default=False)
    reason_for_visit = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Appointment {self.appointment_id} for Patient {self.patient.patient_id}"
    class Meta:
        db_table = 'Appointment'

class Report(models.Model):
    report_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE)
    insurance = models.ForeignKey(Insurance, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Report {self.report_id} for Patient {self.patient.patient_id}"
    class Meta:
        db_table = 'Report'