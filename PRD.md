## **Product Requirements Document: "Learnify" LMS Platform**

**Version:** 1.0
**Date:** October 26, 2023
**Author:** \[Your Name/Team]
**Status:** Draft

### 1. Introduction & Vision

This document outlines the requirements for **Learnify**, a modern, secure, and scalable Learning Management System (LMS). The platform will be built using a FastAPI backend, providing a robust API for a future web or mobile front-end. The core vision is to create a seamless experience for students to learn, for instructors to share their knowledge, and for administrators to manage the platform efficiently. The system prioritizes security, clear role-based access control, and a scalable architecture.

### 2. Goals & Objectives

* **Primary Goal:** To develop a functional backend for an LMS that supports user registration, course creation, and student enrollment.
* **Security Objective:** Implement industry-standard authentication and precise authorization to protect user data and platform integrity.
* **Performance Objective:** Ensure fast API response times by leveraging asynchronous programming (FastAPI) and caching (Redis).
* **Scalability Objective:** Build a foundation that can be extended with more features in the future (e.g., payments, quizzes, video hosting).
* **Usability Objective:** Provide a clear and logical API structure that is easy for front-end developers to consume.

### 3. User Personas & Roles

The system will support four distinct user roles with a clear hierarchy of permissions.

| Role                      | Persona                     | Description & Core Needs                                                                                                                                        |
| :------------------------ | :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Normal User (Student)** | **Alex, the Learner**       | A university student or professional looking to acquire new skills. Needs to easily browse, register for, and access course materials.                          |
| **Instructor**            | **Dr. Evans, the Educator** | A subject matter expert who wants to create and manage their own courses. Needs tools to upload content, describe the course, and see who has enrolled.         |
| **Staff User**            | **Brenda, the Coordinator** | An administrative assistant. Needs broader permissions than an instructor to help manage multiple courses, users, and content, but without full system control. |
| **Admin User**            | **Sam, the Super Admin**    | A system administrator responsible for the entire platform's health and integrity. Needs unrestricted access to manage all users, courses, and system settings. |

### 4. Functional Requirements

#### 4.1. User Authentication & Identity Management

* **FR-1: User Registration:**

  * Users can register using an `email address` and a `password`.
  * Password must be securely hashed (e.g., using bcrypt) before storing.
  * Upon registration, an OTP (One-Time Password) will be generated and sent to the user's email via SendGrid for verification.
  * The user account remains inactive until the email is verified with the OTP.

* **FR-2: User Login:**

  * Users can log in with their verified `email` and `password`.
  * Upon successful login, the system will create a secure, HttpOnly cookie containing the user's session ID.
  * The session will include `user_id`, `role`, and an expiration timestamp.
  * Cookies will have the `Secure`, `HttpOnly`, and `SameSite=Strict` attributes for enhanced security.

* **FR-3: User Logout:**

  * Provide an endpoint to invalidate the user's session by deleting the associated cookie.
  * Optionally, store the session ID in Redis and mark it as invalid until expiration to prevent reuse.

* **FR-4: Password Reset:**

  * A "Forgot Password" feature must be available.
  * User enters their email address.
  * If the email exists, a unique, time-sensitive password reset token is generated and sent to their email.
  * The user clicks the link/uses the token to set a new password.

* **FR-5: User Profile Management:**

  * Authenticated users can view their own profile information (e.g., name, email).
  * Authenticated users can update their non-critical profile information (e.g., name, bio). Changing email would require a re-verification process.

#### 4.2. Authorization & Role-Based Access Control (RBAC)

* **FR-6: Precise Permissions:**

  * Access to API endpoints and resources will be strictly controlled based on the user's role (`Student`, `Instructor`, `Staff`, `Admin`).
  * Middleware in FastAPI will verify the session ID from the cookie and ensure the user's role matches the required permissions for each endpoint.

* **FR-7: Role Permission Matrix:**

| Action                              | Student | Instructor | Staff | Admin |
| :---------------------------------- | :------ | :--------- | :---- | :---- |
| **User Management**                 |         |            |       |       |
| View Own Profile                    | ✅       | ✅          | ✅     | ✅     |
| Edit Own Profile                    | ✅       | ✅          | ✅     | ✅     |
| View All Users                      | ❌       | ❌          | ✅     | ✅     |
| Edit Other Users                    | ❌       | ❌          | ✅     | ✅     |
| Change User Roles                   | ❌       | ❌          | ❌     | ✅     |
| Delete User                         | ❌       | ❌          | ✅     | ✅     |
| **Course Management**               |         |            |       |       |
| View Published Courses              | ✅       | ✅          | ✅     | ✅     |
| Create Course                       | ❌       | ✅          | ✅     | ✅     |
| Edit Own Course                     | ❌       | ✅          | ❌     | ❌     |
| Edit Any Course                     | ❌       | ❌          | ✅     | ✅     |
| Delete Course                       | ❌       | ❌          | ✅     | ✅     |
| **Enrollment**                      |         |            |       |       |
| Enroll in a Course                  | ✅       | ❌          | ❌     | ❌     |
| Un-enroll from a Course             | ✅       | ❌          | ❌     | ❌     |
| View Enrolled Students (Own Course) | ❌       | ✅          | ✅     | ✅     |

#### 4.3. Course Management ("Course Store")

* **FR-8: Course Creation:**

  * `Instructors`, `Staff`, and `Admins` can create a new course.
  * A course must have: `title`, `description`, `instructor_id` (auto-filled for instructors), and `status` (e.g., Draft, Published).
  * (Future Scope: price, cover image, curriculum structure like modules/lessons).

* **FR-9: Course Visibility & Listing:**

  * All users can view a list of `Published` courses.
  * The list should be paginated to handle large numbers of courses.
  * Users can view the detailed page of a single `Published` course.

* **FR-10: Course Updates:**

  * An `Instructor` can only edit their own courses.
  * `Staff` and `Admins` can edit any course.

* **FR-11: Course Deletion:**

  * Only `Staff` and `Admins` can delete courses. This is a privileged action to prevent accidental data loss.

#### 4.4. Student Enrollment

* **FR-12: Course Enrollment:**

  * A logged-in `Student` can enroll in any `Published` course.
  * The system must prevent duplicate enrollments.
  * The system will create a record linking the `user_id` and `course_id`.

* **FR-13: View Enrolled Courses:**

  * A `Student` can view a list of all courses they are enrolled in.

### 5. Non-Functional Requirements

* **NFR-1: Security:**

  * **Authentication:** Session-based authentication with secure cookies for all protected API routes.
  * **Password Storage:** All passwords must be hashed using a strong, salted algorithm (e.g., `bcrypt`).
  * **Data Validation:** Use Pydantic models for strict request body validation to prevent injection attacks.
  * **CSRF Protection:** CSRF tokens must be implemented and required for any state-changing API endpoint that could be called from a web browser session (e.g., changing password, updating profile via form).
  * **Communication:** All communication must be over HTTPS in production.

* **NFR-2: Performance:**

  * **API Response Time:** Average API response time should be under 200ms for standard requests.
  * **Caching:** Redis will be used for:

    * Caching frequently accessed, non-critical data (e.g., list of published courses).
    * Storing session invalidation records for logout.
    * Storing temporary data like OTPs and password reset tokens.

* **NFR-3: Database:**

  * **DBMS:** Postgre will be the relational database.
  * **Schema:** The database schema must be well-designed with appropriate indexing for performance. Use a migration tool like Alembic to manage schema changes.

* **NFR-4: Email Notifications:**

  * **Service:** SendGrid will be used as the email delivery service.
  * **Templates:** Email templates should be used for OTPs, password resets, and welcome emails.

### 6. Technology Stack

* **Backend Framework:** FastAPI (Python)
* **Database:** Postgre
* **Caching / In-Memory Store:** Redis
* **Email Service:** SendGrid
* **Data Validation:** Pydantic
* **Database ORM:** SQLAlchemy with Alembic for migrations
* **Authentication:** `passlib` for hashing, session-based cookies
* **Async Support:** `asyncio`, `httpx` (for external API calls if needed)

### 7. High-Level System Architecture

1. **Client (Web/Mobile App):** Interacts with the FastAPI backend via a RESTful API.
2. **FastAPI Backend:** The core of the application. It handles business logic, authentication, and authorization.
3. **Postgre Database:** The persistent source of truth for all core data (users, courses, enrollments).
4. **Redis:** A high-speed cache for shared/temporary resources like sessions, OTPs, and API response caches.
5. **SendGrid:** An external service used by the FastAPI backend to dispatch emails for notifications.

### 8. Initial API Endpoint Specification (Draft)

* `POST /auth/register` - Create a new user.
* `POST /auth/verify-email` - Verify email using OTP.
* `POST /auth/login` - Authenticate and receive session cookie. **(Requires CSRF token if form-based)**
* `POST /auth/logout` - Logout and invalidate the session cookie.
* `POST /auth/forgot-password` - Request a password reset email.
* `POST /auth/reset-password` - Set a new password using a reset token.

---

* `GET /users/me` - Get current user's profile.
* `PUT /users/me` - Update current user's profile. **(Requires CSRF token)**
* `GET /admin/users` - \[Admin, Staff] Get list of all users.
* `PUT /admin/users/{user_id}` - \[Admin, Staff] Update a user's details.
* `DELETE /admin/users/{user_id}` - \[Admin, Staff] Delete a user.

---

* `GET /courses` - Get a paginated list of published courses.
* `POST /courses` - \[Instructor, Staff, Admin] Create a new course. **(Requires CSRF token)**
* `GET /courses/{course_id}` - Get details for a single course.
* `PUT /courses/{course_id}` - \[Instructor(Own), Staff, Admin] Update a course. **(Requires CSRF token)**
* `DELETE /courses/{course_id}` - \[Staff, Admin] Delete a course.

---

* `POST /courses/{course_id}/enroll` - \[Student] Enroll in a course.
* `GET /users/me/courses` - \[Student] Get list of courses the current user is enrolled in.

### 9. Future Scope / V2 Features

* Payment integration for paid courses (Stripe/PayPal).
* Course content management (modules, lessons, video uploads).
* Student progress tracking.
* Quizzes and assignments.
* Review and rating system for courses.
* Advanced admin dashboard with analytics.

### 10. Success Metrics

* **User Adoption:** Number of active users (students and instructors).
* **Content Growth:** Number of courses created and published per month.
* **System Stability:** API uptime > 99.9%.
* **Performance:** API latency remains below defined thresholds under load.
