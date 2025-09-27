// Use DBML to define your database structure
// Docs: https://dbml.dbdiagram.io/docs

// --- Enums ---
enum UserRole {
  STUDENT
  INSTRUCTOR
  STAFF
  ADMIN
}

enum InvoiceStatus {
  DUE
  PAID
  OVERDUE
  CANCELLED
}

enum PaymentStatus {
  PENDING
  SUCCESSFUL
  FAILED
}

// --- NEW Enums for Attendance System ---
enum CardStatus {
  ACTIVE
  INACTIVE
  LOST
  DAMAGED
}

enum AttendanceType {
  CHECK_IN
  CHECK_OUT
}


// --- ORIGINAL TABLES (UNCHANGED) ---

Table users {
  id integer [pk, increment]
  email string [unique, not null]
  hashed_password string [not null]
  role UserRole [not null]
  need_change_email bool [not null, default: false]
  need_change_password bool [not null, default: false]
  created_at timestamp [not null, default: `now(quay video ddi)`]
  last_login_at timestamp [not null, default: `now()`]
}

Table user_profiles {
  user_id integer [pk, ref: - users.id]
  first_name string [not null]
  last_name string [not null]
  date_of_birth timestamp
  avatar string
}

Table courses {
  id integer [pk, increment]
  creator_id integer [not null, ref: > users.id]
  title string [not null]
  description text
  created_at timestamp [not null, default: `now()`]
  location string 
  start_date timestamp
  teacher_name string 
  price decimal(10, 2) [note: 'Used if payment_type is ONE_TIME']
  preview_picture_path string [note: 'Path to course preview picture for lazy loading']
}

Table enrollments {
  id integer [pk, increment]
  student_id integer [not null, ref: > users.id]
  course_id integer [not null, ref: > courses.id]
  enrolled_at timestamp [not null, default: `now()`]
  is_active boolean [default: true] 
  
  indexes {
    (student_id, course_id) [unique]
  }
}

Table course_edit_permissions {
  course_id integer [pk, ref: > courses.id]
  instructor_id integer [pk, ref: > users.id]
  granted_by integer [ref: > users.id]
  granted_at timestamp [not null, default: `now()`]
}

Table course_payment_period {
  id integer [pk, increment]
  course_id integer [ref: > courses.id]
  amount decimal(10, 2)
  created_at timestamp 
  created_by integer [ref: > users.id]
}

Table invoices {
  id integer [pk, increment]
  enrollment_id integer [not null, ref: > enrollments.id] 
  payment_period_id integer [not null, ref: > course_payment_period.id] 
  status InvoiceStatus [not null, default: 'DUE']
  amount_due decimal(10, 2) [not null] 
  created_at timestamp [not null, default: `now()`]
  indexes {
    (enrollment_id, payment_period_id) [unique]
  }
}

Table payments {
  id integer [pk, increment]
  invoice_id integer [not null, ref: > invoices.id]
  status PaymentStatus [not null, default: 'PENDING']
  amount decimal(10, 2) [not null]
  provider_reference string [unique, note: 'ID from Stripe, PayPal, etc.']
  created_at timestamp [not null, default: `now()`]
}


// --- Course Documents Table ---
Table course_documents {
  id integer [pk, increment]
  course_id integer [not null, ref: > courses.id]
  document_path string [note: 'Path to document file']
  document_name string [not null]
  document_type string [note: 'File type: PDF, DOCX, etc.']
  document_size integer [note: 'File size in bytes']
  uploaded_by integer [not null, ref: > users.id]
  uploaded_at timestamp [not null, default: `now()`]
  is_active boolean [default: true]
  
  indexes {
    (course_id, is_active)
  }
}

// --- ADDITIONS FOR ATTENDANCE TRACKING SYSTEM (Simplified) ---
// The following tables implement the best-practice approach for attendance tracking.

// 1. Table to manage the physical cards
Table attendance_cards {
  card_uid string [pk, note: 'Unique ID from the card (RFID/NFC UID, Barcode). This is the physical identifier.']
  status CardStatus [not null, default: 'INACTIVE']
  issued_at timestamp [not null, default: `now()`, note: 'When the card was first created in the system']
  notes text

  note: 'Manages the lifecycle of each physical attendance card.'
}

// 2. Table to link a card to a student over a period of time (The Key Table)
Table card_assignments {
  id integer [pk, increment]
  student_id integer [not null, ref: > users.id]
  card_uid string [not null, ref: > attendance_cards.card_uid]
  assigned_at timestamp [not null, default: `now()`, note: 'The moment this card was given to the student']
  revoked_at timestamp [note: 'The moment the card was returned or deactivated for this student. NULL if currently active.']

  note: 'This table tracks the history of which student used which card and when. This solves the card re-issuance problem.'
  indexes {
    // A student can only have one active card at a time
    (student_id, revoked_at) 
    // A card can only be actively assigned to one student at a time
    (card_uid, revoked_at)
  }
}

// 3. The main table to log every single swipe event
Table attendance_records {
  id integer [pk, increment]
  // CRITICAL: We store the student_id directly for historical integrity.
  student_id integer [not null, ref: > users.id]
  
  swiped_at timestamp [not null, default: `now()`, note: 'The exact moment of the swipe']
  type AttendanceType [not null]
  
  // This field is for auditing and richer data
  card_uid_used string [not null, note: 'Which card UID was used for this specific swipe']
  
  note: 'An immutable log of every attendance event. Linked directly to a student, not a card assignment.'
}

Ref: "payments"."id" < "payments"."status"

Ref: "invoices"."id" < "invoices"."status"

Ref: "enrollments"."id" < "enrollments"."enrolled_at"