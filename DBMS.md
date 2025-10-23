// Use DBML to define your database structure
// Docs: https://dbml.dbdiagram.io/docs
//
// SCHEMA UPDATE: All integer auto-incrementing primary keys have been replaced
// with UUIDv7. This enhances security by making IDs non-guessable and prepares
// the system for distributed environments. In a PostgreSQL implementation,
// this would use the `uuid_generate_v7()` function from an extension.

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

enum DayOfWeek {
  MONDAY
  TUESDAY
  WEDNESDAY
  THURSDAY
  FRIDAY
  SATURDAY
  SUNDAY
}


// --- TABLES ---

Table users {
  id uuid [pk, default: `uuid_generate_v7()`]
  email string [unique, not null]
  hashed_password string [not null]
  role UserRole [not null]
  need_change_email bool [not null, default: false]
  need_change_password bool [not null, default: false]
  created_at timestamp [not null, default: `now()`]
  last_login_at timestamp [not null, default: `now()`]
}

Table user_profiles {
  user_id uuid [pk, ref: - users.id]
  first_name string [not null]
  last_name string [not null]
  date_of_birth timestamp
  avatar string
  current_school string [note: 'Trường học sinh đang theo học']
  current_grade string [note: 'Lớp chính khóa của học sinh (vd: 10A1)']
  default_discount_percentage decimal(5, 2) [default: 0, note: 'Mức giảm giá mặc định từ trung tâm cho học sinh này']
}

Table courses {
  id uuid [pk, default: `uuid_generate_v7()`]
  creator_id uuid [not null, ref: > users.id]
  title string [not null]
  description text
  created_at timestamp [not null, default: `now()`]
  start_date timestamp [note: 'Ngày khai giảng tổng thể của khóa học']
  teacher_name string 
  price decimal(10, 2)
  preview_picture_path string
  group_chat_link string [note: 'Link nhóm Zalo, Facebook, etc. của lớp học']
}

Table enrollments {
  id uuid [pk, default: `uuid_generate_v7()`]
  student_id uuid [not null, ref: > users.id]
  course_id uuid [not null, ref: > courses.id]
  enrolled_at timestamp [not null, default: `now()`]
  is_active boolean [default: true] 
  discount_percentage decimal(5, 2) [default: 0, not null, note: 'Tỉ lệ miễn giảm học phí áp dụng cho lần đăng ký này']
  discount_reason text [note: 'Lý do miễn giảm']
  discount_approved_by uuid [ref: > users.id, note: 'ID của người duyệt miễn giảm']
  
  indexes {
    (student_id, course_id) [unique]
  }
}

Table course_edit_permissions {
  course_id uuid [pk, ref: > courses.id]
  instructor_id uuid [pk, ref: > users.id]
  granted_by uuid [ref: > users.id]
  granted_at timestamp [not null, default: `now()`]
}

Table course_payment_period {
  id uuid [pk, default: `uuid_generate_v7()`]
  course_id uuid [ref: > courses.id]
  amount decimal(10, 2)
  created_at timestamp 
  created_by uuid [ref: > users.id]
}

Table invoices {
  id uuid [pk, default: `uuid_generate_v7()`]
  enrollment_id uuid [not null, ref: > enrollments.id] 
  payment_period_id uuid [not null, ref: > course_payment_period.id] 
  status InvoiceStatus [not null, default: 'DUE']
  amount_due decimal(10, 2) [not null, note: 'Số tiền phải trả SAU KHI đã áp dụng miễn giảm']
  created_at timestamp [not null, default: `now()`]
  indexes {
    (enrollment_id, payment_period_id) [unique]
  }
}

Table payments {
  id uuid [pk, default: `uuid_generate_v7()`]
  invoice_id uuid [not null, ref: > invoices.id]
  status PaymentStatus [not null, default: 'PENDING']
  amount decimal(10, 2) [not null]
  provider_reference string [unique, note: 'ID from Stripe, PayPal, etc.']
  created_at timestamp [not null, default: `now()`]
}

Table course_documents {
  id uuid [pk, default: `uuid_generate_v7()`]
  course_id uuid [not null, ref: > courses.id]
  document_path string [note: 'Path to document file']
  document_name string [not null]
  document_type string [note: 'File type: PDF, DOCX, etc.']
  document_size integer [note: 'File size in bytes']
  uploaded_by uuid [not null, ref: > users.id]
  uploaded_at timestamp [not null, default: `now()`]
  is_active boolean [default: true]
  
  indexes {
    (course_id, is_active)
  }
}

Table attendance_cards {
  card_uid string [pk, note: 'Unique ID from the card (RFID/NFC UID, Barcode). This is the physical identifier.']
  status CardStatus [not null, default: 'INACTIVE']
  issued_at timestamp [not null, default: `now()`]
  notes text
  note: 'Manages the lifecycle of each physical attendance card.'
}

Table card_assignments {
  id uuid [pk, default: `uuid_generate_v7()`]
  student_id uuid [not null, ref: > users.id]
  card_uid string [not null, ref: > attendance_cards.card_uid]
  assigned_at timestamp [not null, default: `now()`]
  revoked_at timestamp [note: 'NULL if currently active.']
  note: 'Tracks the history of which student used which card and when.'
  indexes {
    (student_id, revoked_at) 
    (card_uid, revoked_at)
  }
}

Table attendance_records {
  id uuid [pk, default: `uuid_generate_v7()`]
  student_id uuid [not null, ref: > users.id]
  swiped_at timestamp [not null, default: `now()`]
  type AttendanceType [not null]
  card_uid_used string [not null, note: 'Which card UID was used for this specific swipe']
  note: 'An immutable log of every attendance event.'
}

Table guardians {
  id uuid [pk, default: `uuid_generate_v7()`]
  full_name string [not null]
  phone_number string [unique, not null]
  notes text [note: 'Ghi chú cho team sale: công việc, sở thích, thói quen của phụ huynh...']
  created_at timestamp [not null, default: `now()`]
}

Table student_guardian_relationships {
  student_id uuid [pk, ref: > users.id]
  guardian_id uuid [pk, ref: > guardians.id]
  relationship_type string [note: 'e.g., "Father", "Mother", "Guardian"']
}

Table branches {
  id uuid [pk, default: `uuid_generate_v7()`]
  name string [unique, not null, note: 'Tên cơ sở, ví dụ: "Cơ sở Cầu Giấy"']
  address string [not null]
  contact_info string
}

Table rooms {
  id uuid [pk, default: `uuid_generate_v7()`]
  branch_id uuid [not null, ref: > branches.id]
  room_number string [not null, note: 'Số phòng hoặc tên phòng, ví dụ: "P101"']
  capacity integer
  indexes {
    (branch_id, room_number) [unique]
  }
}

Table course_schedules {
  id uuid [pk, default: `uuid_generate_v7()`]
  course_id uuid [not null, ref: > courses.id]
  room_id uuid [not null, ref: > rooms.id]
  day_of_week DayOfWeek [not null]
  start_time time [not null, note: 'e.g., 17:00:00']
  end_time time [not null, note: 'e.g., 18:30:00']
  note: 'A course meeting twice a week will have two records here.'
  indexes {
    (course_id, day_of_week, start_time) [unique]
  }
}