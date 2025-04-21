from django.db import connection

# 1) Raw SQL trigger definitions for performing 3 tasks:
#    - After inserting a Patient, automatically create an empty Patient_Contact
#    - After inserting a Staff_Details, automatically create an empty Staff_Contact
#    - After inserting a Drug, automatically populate Drug_Interaction
TRIGGERS = [
    r"""
    CREATE TRIGGER trg_patient_after_insert
    AFTER INSERT ON Patient
    FOR EACH ROW
    BEGIN
      INSERT INTO Patient_Contact(patient_id, phone_number, email, address)
      VALUES (NEW.patient_id, '', '', '');
    END
    """,
    r"""
    CREATE TRIGGER trg_staff_after_insert
    AFTER INSERT ON Staff_Details
    FOR EACH ROW
    BEGIN
      INSERT INTO Staff_Contact(staff_id, phone_number, email, address)
      VALUES (NEW.staff_id, '', '', '');
    END
    """,
    r"""
            CREATE TRIGGER trg_drug_interaction_insert
    AFTER INSERT ON Drug
    FOR EACH ROW
    BEGIN
      INSERT INTO Drug_Interaction(drug_1_id, drug_2_id, interaction_details, severity_level, alert)
        SELECT NEW.drug_id, d.drug_id, 'No known interaction', 'Low', 'No alert'
        FROM Drug d WHERE d.drug_id <> NEW.drug_id;
    END
    """
]

def init_triggers():
    """Execute each CREATE TRIGGER statement if it doesn’t already exist."""
    with connection.cursor() as cursor:
        for sql in TRIGGERS:
            try:
                cursor.execute(sql)
            except Exception:
                # most likely trigger already exists
                pass

# 2) Generic CRUD helpers via raw SQL

def list_records(table_name, where=None, params=None):
    """
    Return rows from the given table as a list of dicts.
    
    :param table_name:   Name of the table to query (trusted input only!)
    :param where:        Optional SQL condition (e.g. "patient_id = %s")
    :param params:       Optional list of parameters to bind to the query
    :return:             List of dicts, one per row
    Usage examples:
        # All patients
        list_records('Patient')
        
        # Contacts for a particular patient
        list_records(
            'Patient_Contact',
            where='patient_id = %s',
            params=[patient_id]
        )
    """
    sql = f"SELECT * FROM {table_name}"
    if where:
        sql += f" WHERE {where}"
    params = params or []

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        cols = [col[0] for col in cursor.description]
        return [
            dict(zip(cols, row))
            for row in cursor.fetchall()
        ]

def get_record(table_name, pk_name, pk_value):
    """
    Return a single row (dict) from table_name where pk_name = pk_value.
    Usage: get_record('Patient', 'patient_id', 5)
    """
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM {table_name} WHERE {pk_name} = %s",
            [pk_value]
        )
        row = cursor.fetchone()
        if not row:
            return None
        cols = [col[0] for col in cursor.description]
        return dict(zip(cols, row))

def create_record(table_name, fields, values):
    """
    Insert into table_name (fields...) values (values...)
    Returns the newly inserted row’s AUTO_INCREMENT ID.
    Usage:
      create_record(
        'Patient',
        ['insurance_info','emergency_contact','ehr_link','feedback_rating','registration_date'],
        ['John Doe','Acme Ins.', '1234567890','/ehr/1',4,'2025-04-17']
      )
    """
    cols_str = ', '.join(fields)
    placeholders = ', '.join(['%s'] * len(values))
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})",
            values
        )
        # MySQL returns lastrowid on cursor
        return cursor.lastrowid

def update_record(table_name, fields, values, pk_name, pk_value):
    """
    Update table_name set field1=%s, field2=%s... where pk_name = pk_value.
    Usage:
      update_record(
        'Patient',
        ['insurance_info'],
        ['Jane Doe','New Ins.'],
        'patient_id', 5
      )
    """
    set_clause = ', '.join(f"{f} = %s" for f in fields)
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table_name} SET {set_clause} WHERE {pk_name} = %s",
            values + [pk_value]
        )
def check_interactions_for_drugs(drug_ids):
    if len(drug_ids) < 2:
        return []

    # we’ll look for any stored interaction where both drugs appear, in either order
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                d1.drug_name, 
                d2.drug_name, 
                di.interaction_details, 
                di.severity_level
            FROM Drug_Interaction di
            JOIN Drug d1 ON di.drug_1_id = d1.drug_id
            JOIN Drug d2 ON di.drug_2_id = d2.drug_id
            WHERE 
                (di.drug_1_id IN %s AND di.drug_2_id IN %s)
             OR (di.drug_1_id IN %s AND di.drug_2_id IN %s)
        """, [tuple(drug_ids), tuple(drug_ids), tuple(drug_ids), tuple(drug_ids)])

        interactions = []
        for drug1, drug2, details, severity in cursor.fetchall():
            interactions.append({
                'drug1':    drug1,
                'drug2':    drug2,
                'details':  details,
                'severity': severity,
            })
        return interactions
