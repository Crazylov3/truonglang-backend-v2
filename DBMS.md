// Use DBML to define your database structure
// Docs: https://dbml.dbdiagram.io/docs

// --- Enums ---
enum UserRole {
  STUDENT
  INSTRUCTOR
  STAFF
  ADMIN
}

enum PaymentStatus {
  PENDING
  PAID
  FAILED
  REFUNDED
}

// --- Core Tables ---

Table users {
  id integer [pk, increment]
  email string [unique, not null]
  hashed_password string [not null]
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
  
  // For ONE_TIME payments
  price decimal(10, 2) [note: 'Used if payment_type is ONE_TIME']
}

Table enrollments {
  id integer [pk, increment]
  student_id integer [not null, ref: > users.id]
  course_id integer [not null, ref: > courses.id]
  enrolled_at timestamp [not null, default: `now()`]
  // An enrollment can be active even if a payment is due.
  // The subscription status will control access.
  is_active boolean [default: true] 
  
  indexes {
    (student_id, course_id) [unique]
  }
}

// --- Modified Payments Table ---
Table payments {
  id integer [pk, increment]
  user_id integer [not null, ref: > users.id]
  course_id integer [not null, ref: > courses.id, note: 'Denormalized for easy lookup']
  
  amount decimal(10, 2) [not null]
  status PaymentStatus [not null, default: 'PENDING']
  provider_reference string [unique, note: 'ID from Stripe, PayPal, etc.']
  created_at timestamp [not null, default: `now()`]
  updated_at timestamp [not null, default: `now()`]
  
  note: 'Records every single payment attempt.'
}