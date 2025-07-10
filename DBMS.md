// Use DBML to define your database structure
// Docs: https://dbml.dbdiagram.io/docs

// --- Enums ---
enum UserRole {
  STUDENT
  INSTRUCTOR
  STAFF
  ADMIN
}

// --- NEW Enums Required for Billing ---
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


// --- UNCHANGED ORIGINAL TABLES ---

Table users {
  id integer [pk, increment]
  email string [unique, not null]
  hashed_password string [not null]
  role UserRole [not null]
  created_at timestamp [not null, default: `now()`]
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


// --- REQUIRED CHANGES FOR BILLING LOGIC ---

// 1. YOUR ORIGINAL TABLE (Unchanged) - This is the trigger
Table course_payment_period {
  id integer [pk, increment]
  course_id integer [ref: > courses.id]
  amount decimal(10, 2)
  created_at timestamp 
  created_by integer [ref: > users.id]
  
  // Suggested additions for clarity:
  // title string [note: 'e.g., "Payment for November"']
  // due_date date
}

// 2. NEW TABLE (Required) - This is the bridge
Table invoices {
  id integer [pk, increment]
  // Links to the specific student's enrollment
  enrollment_id integer [not null, ref: > enrollments.id] 
  // Links to the payment period created by the instructor
  payment_period_id integer [not null, ref: > course_payment_period.id] 
  
  status InvoiceStatus [not null, default: 'DUE']
  // The amount is copied here to prevent issues if the original period's amount changes
  amount_due decimal(10, 2) [not null] 
  created_at timestamp [not null, default: `now()`]

  note: 'A specific, trackable bill for one student. Generated when a course_payment_period is created.'
  indexes {
    (enrollment_id, payment_period_id) [unique]
  }
}

// 3. MODIFIED PAYMENTS TABLE (Required)
Table payments {
  id integer [pk, increment]
  // --- CRITICAL CHANGE: A payment is now made against an INVOICE, not a user.
  invoice_id integer [not null, ref: > invoices.id]

  // --- CRITICAL ADDITION: You need to know if the payment was successful.
  status PaymentStatus [not null, default: 'PENDING']

  amount decimal(10, 2) [not null]
  provider_reference string [unique, note: 'ID from Stripe, PayPal, etc.']
  created_at timestamp [not null, default: `now()`]
  note: 'Records a payment attempt against a specific invoice.'
}