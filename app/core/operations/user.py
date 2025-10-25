"""User database operations."""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date
import logging
import csv
import io
from app.models.user import User, UserRole
from app.models.user_profile import UserProfile
from app.core.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.error(f"Error getting user by email: {email}", exc_info=True)
        return None


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get user by ID."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.error(f"Error getting user by ID: {user_id}", exc_info=True)
        return None

async def get_user_by_public_id(db: AsyncSession, public_id: int) -> Optional[User]:
    """Get user by public ID."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.public_id == public_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError:
        logger.error(f"Error getting user by public ID: {public_id}", exc_info=True)
        return None


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    try:
        user = await get_user_by_email(db, email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    except SQLAlchemyError:
        logger.error(f"Error authenticating user: {email}", exc_info=True)
        return None


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str = None,
    last_name: str = None,
    role: UserRole = UserRole.STUDENT,
    date_of_birth=None
) -> User:
    """Create a new user with optional profile."""
    try:
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create user object
        user = User(
            email=email,
            hashed_password=hashed_password,
            role=role,
            last_login_at=datetime.utcnow()  # Set last_login_at to current time
        )
        
        db.add(user)
        await db.flush()  # Get the user ID
        
        # Create user profile if names are provided
        if first_name and last_name:
            profile = UserProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth
            )
            db.add(profile)
        
        await db.commit()
        await db.refresh(user)
        
        # Load the profile relationship
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user.id)
        )
        user_with_profile = result.scalar_one()
        
        return user_with_profile
        
    except SQLAlchemyError as e:
        await db.rollback()
        raise e


async def update_user_password(db: AsyncSession, email: str, new_password: str) -> bool:
    """Update user's password."""
    try:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_last_login(db: AsyncSession, user_id: int) -> bool:
    """Update user's last login timestamp."""
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.last_login_at = datetime.utcnow()
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_role(db: AsyncSession, email: str, new_role: UserRole) -> bool:
    """Update user's role."""
    try:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        user.role = new_role
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_role_by_id(db: AsyncSession, user_id: int, new_role: UserRole) -> bool:
    """Update user's role by ID."""
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        user.role = new_role
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def update_user_profile(
    db: AsyncSession,
    user_id: int,
    first_name: str = None,
    last_name: str = None,
    date_of_birth=None,
    avatar: str = None
) -> bool:
    """Update user profile information."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Create profile if it doesn't exist
        if not user.profile:
            if first_name and last_name:
                profile = UserProfile(
                    user_id=user.id,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date_of_birth,
                    avatar=avatar
                )
                db.add(profile)
        else:
            # Update existing profile
            if first_name is not None:
                user.profile.first_name = first_name
            if last_name is not None:
                user.profile.last_name = last_name
            if date_of_birth is not None:
                user.profile.date_of_birth = date_of_birth
            if avatar is not None:
                user.profile.avatar = avatar
        
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def delete_user(db: AsyncSession, email: str) -> bool:
    """Delete user and their profile."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User with email {email} not found")
            return False
        
        # Delete dependent rows for NOT NULL FKs before deleting the user
        # 1) Delete enrollments and their invoices/payments
        try:
            from app.models import Enrollment
            from app.models.payment import Invoice, Payment
            enrollments_result = await db.execute(
                select(Enrollment).options(
                    selectinload(Enrollment.invoices).selectinload(Invoice.payments)
                ).where(Enrollment.student_id == user.id)
            )
            enrollments = enrollments_result.scalars().all()
            for enrollment in enrollments:
                # Delete payments for each invoice
                for invoice in list(enrollment.invoices or []):
                    for payment in list(invoice.payments or []):
                        await db.delete(payment)
                    await db.delete(invoice)
                await db.delete(enrollment)
        except Exception:
            # Log and continue to rollback in outer except if needed
            logger.error("Error deleting user enrollments/invoices/payments", exc_info=True)

        # Delete profile first if it exists (due to foreign key constraints)
        if user.profile:
            await db.delete(user.profile)
        
        await db.delete(user)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        logger.error(f"Error deleting user with email {email}", exc_info=True)
        await db.rollback()
        return False


async def delete_user_by_id(db: AsyncSession, user_id: int) -> bool:
    """Delete user by ID and their profile."""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Delete dependent rows for NOT NULL FKs before deleting the user
        # 1) Delete enrollments and their invoices/payments
        try:
            from app.models import Enrollment
            from app.models.payment import Invoice, Payment
            enrollments_result = await db.execute(
                select(Enrollment).options(
                    selectinload(Enrollment.invoices).selectinload(Invoice.payments)
                ).where(Enrollment.student_id == user.id)
            )
            enrollments = enrollments_result.scalars().all()
            for enrollment in enrollments:
                # Delete payments for each invoice
                for invoice in list(enrollment.invoices or []):
                    for payment in list(invoice.payments or []):
                        await db.delete(payment)
                    await db.delete(invoice)
                await db.delete(enrollment)
        except Exception:
            # Log and continue to rollback in outer except if needed
            logger.error("Error deleting user enrollments/invoices/payments", exc_info=True)

        # Delete profile first if it exists (due to foreign key constraints)
        if user.profile:
            await db.delete(user.profile)
        
        await db.delete(user)
        await db.commit()
        return True
        
    except SQLAlchemyError:
        await db.rollback()
        return False


async def list_users(
    db: AsyncSession,
    role: Optional[UserRole] = None,
    public_id: Optional[int] = None,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    current_school: Optional[str] = None,
    current_grade: Optional[str] = None,
    default_discount_percentage: Optional[float] = None,
    limit: int = 50,
    offset: int = 0
) -> List[User]:
    """List users with optional filtering and search."""
    try:
        from sqlalchemy import or_, and_
        query = select(User).options(selectinload(User.profile)).order_by(User.created_at.desc())
        
        conditions = []
        
        if role:
            conditions.append(User.role == role)
        
        if public_id:
            conditions.append(User.public_id == public_id)
        
        if email:
            conditions.append(User.email.ilike(f"%{email}%"))
        
        if first_name:
            conditions.append(User.profile.has(UserProfile.first_name.ilike(f"%{first_name}%")))
        
        if last_name:
            conditions.append(User.profile.has(UserProfile.last_name.ilike(f"%{last_name}%")))
        
        if current_school:
            conditions.append(User.profile.has(UserProfile.current_school.ilike(f"%{current_school}%")))
        
        if current_grade:
            conditions.append(User.profile.has(UserProfile.current_grade.ilike(f"%{current_grade}%")))
        
        if default_discount_percentage is not None:
            conditions.append(User.profile.has(UserProfile.default_discount_percentage > default_discount_percentage))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        return users
        
    except SQLAlchemyError:
        return []


async def count_users(
    db: AsyncSession, 
    role: Optional[UserRole] = None,
    public_id: Optional[int] = None,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    current_school: Optional[str] = None,
    current_grade: Optional[str] = None,
    default_discount_percentage: Optional[float] = None
) -> int:
    """Count users with optional filtering and search."""
    try:
        from sqlalchemy import or_, and_
        query = select(func.count(User.id))
        
        conditions = []
        
        if role:
            conditions.append(User.role == role)
        
        if public_id:
            conditions.append(User.public_id == public_id)
        
        if email:
            conditions.append(User.email.ilike(f"%{email}%"))
        
        if first_name:
            conditions.append(User.profile.has(UserProfile.first_name.ilike(f"%{first_name}%")))
        
        if last_name:
            conditions.append(User.profile.has(UserProfile.last_name.ilike(f"%{last_name}%")))
        
        if current_school:
            conditions.append(User.profile.has(UserProfile.current_school.ilike(f"%{current_school}%")))
        
        if current_grade:
            conditions.append(User.profile.has(UserProfile.current_grade.ilike(f"%{current_grade}%")))
        
        if default_discount_percentage is not None:
            conditions.append(User.profile.has(UserProfile.default_discount_percentage > default_discount_percentage))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await db.execute(query)
        return result.scalar() or 0
        
    except SQLAlchemyError:
        return 0




# Temporal User Operations
async def create_temporal_user(
    db: AsyncSession,
    first_name: str,
    last_name: str,
    date_of_birth: Optional[date] = None,
    current_school: Optional[str] = None,
    current_grade: Optional[str] = None,
    default_discount_percentage: float = 0.0
) -> Optional[Tuple[User, UserProfile, str, str]]:
    """Create a temporal user (student) with auto-generated email and password.
    
    Returns:
        Tuple of (User, UserProfile, email, password) if successful, None otherwise
    """
    try:
        # Create user first to get public_id
        user = User(
            email="temp@temp.com",  # Temporary email, will be updated
            hashed_password="temp",  # Temporary password, will be updated
            role=UserRole.STUDENT
        )
        
        db.add(user)
        await db.flush()  # Flush to get the public_id
        
        # Generate temporal email and password
        temporal_email = f"{user.public_id}@tmp.giaoducthanglong.com"
        temporal_password = f"{user.public_id}@giaoducthanglong"
        
        # Update user with temporal credentials
        user.email = temporal_email
        user.hashed_password = get_password_hash(temporal_password)
        
        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            current_school=current_school,
            current_grade=current_grade,
            default_discount_percentage=default_discount_percentage
        )
        
        db.add(profile)
        await db.commit()
        
        # Refresh user with profile loaded
        await db.refresh(user)
        await db.refresh(profile)
        
        # Ensure profile is attached to user
        user.profile = profile
        
        return user, profile, temporal_email, temporal_password
        
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Error creating temporal user: {e}", exc_info=True)
        return None


async def bulk_create_temporal_users(
    db: AsyncSession,
    csv_content: str
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Create multiple temporal users from CSV content using optimized bulk insertion.
    
    Expected CSV format:
    first_name,last_name,date_of_birth,current_school,current_grade,default_discount_percentage
    
    Returns:
        Tuple of (created_users, failed_rows)
    """
    created_users = []
    failed_rows = []
    
    try:
        # Parse CSV content
        logger.info("Starting bulk temporal user creation from CSV")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)  # Convert to list for better processing
        
        total_rows = len(rows)
        logger.info(f"CSV parsed successfully: {total_rows} rows to process")
        
        # Process in batches for memory efficiency
        batch_size = 500  # Increased batch size for better performance
        total_batches = (total_rows + batch_size - 1) // batch_size
        
        logger.info(f"Processing {total_rows} users in {total_batches} batches of {batch_size}")
        
        start_time = datetime.now()
        
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_rows = rows[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} (rows {batch_start + 1}-{batch_end})")
            
            # Process batch
            batch_created, batch_failed = await _process_user_batch_optimized(
                db, batch_rows, batch_start + 2  # +2 because CSV starts at row 2 (header is row 1)
            )
            
            created_users.extend(batch_created)
            failed_rows.extend(batch_failed)
            
            # Calculate progress
            total_processed = len(created_users) + len(failed_rows)
            progress_percent = (total_processed / total_rows) * 100
            
            # Calculate estimated time remaining
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if total_processed > 0:
                avg_time_per_user = elapsed_time / total_processed
                remaining_users = total_rows - total_processed
                estimated_remaining = avg_time_per_user * remaining_users
                eta_minutes = estimated_remaining / 60
            else:
                eta_minutes = 0
            
            logger.info(
                f"Batch {batch_num} completed: {len(batch_created)} created, {len(batch_failed)} failed. "
                f"Progress: {total_processed}/{total_rows} ({progress_percent:.1f}%) - "
                f"ETA: {eta_minutes:.1f} minutes"
            )
        
        # Final summary
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        success_rate = (len(created_users) / total_rows) * 100 if total_rows > 0 else 0
        
        logger.info(
            f"Bulk user creation completed in {total_time:.2f} seconds. "
            f"Success: {len(created_users)}/{total_rows} ({success_rate:.1f}%), "
            f"Failed: {len(failed_rows)}"
        )
        
        return created_users, failed_rows
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}", exc_info=True)
        return [], [{'row': 0, 'data': {}, 'error': f'CSV parsing error: {str(e)}'}]


async def _process_user_batch_optimized(
    db: AsyncSession,
    rows: List[Dict[str, str]],
    start_row_num: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Process a batch of user rows using optimized bulk operations."""
    created_users = []
    failed_rows = []
    valid_user_data = []
    
    logger.debug(f"Processing batch: {len(rows)} rows starting from row {start_row_num}")
    
    # First pass: validate all rows and prepare data
    validation_start = datetime.now()
    for i, row in enumerate(rows):
        row_num = start_row_num + i
        try:
            # Extract and validate data
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            date_of_birth_str = row.get('date_of_birth', '').strip()
            current_school = row.get('current_school', '').strip() or None
            current_grade = row.get('current_grade', '').strip() or None
            default_discount_percentage = float(row.get('default_discount_percentage', '0.0'))
            
            # Validate required fields
            if not first_name or not last_name:
                failed_rows.append({
                    'row': row_num,
                    'data': row,
                    'error': 'Missing required fields: first_name and last_name'
                })
                continue
            
            # Parse date of birth if provided
            date_of_birth = None
            if date_of_birth_str:
                try:
                    date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
                except ValueError:
                    failed_rows.append({
                        'row': row_num,
                        'data': row,
                        'error': f'Invalid date format: {date_of_birth_str}. Use YYYY-MM-DD'
                    })
                    continue
            
            valid_user_data.append({
                'row_num': row_num,
                'row_data': row,
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': date_of_birth,
                'current_school': current_school,
                'current_grade': current_grade,
                'default_discount_percentage': default_discount_percentage
            })
            
        except Exception as e:
            failed_rows.append({
                'row': row_num,
                'data': row,
                'error': str(e)
            })
    
    validation_time = (datetime.now() - validation_start).total_seconds()
    logger.debug(f"Validation completed in {validation_time:.3f}s: {len(valid_user_data)} valid, {len(failed_rows)} failed")
    
    # Second pass: bulk create users and profiles
    if valid_user_data:
        try:
            db_start = datetime.now()
            logger.debug(f"Starting database operations for {len(valid_user_data)} users")
            
            # Step 1: Create all User objects with unique temporary credentials
            import uuid
            users_to_create = []
            for i, user_data in enumerate(valid_user_data):
                # Use a unique temporary email to avoid constraint violations
                temp_email = f"temp_{uuid.uuid4().hex[:8]}@temp.com"
                user = User(
                    email=temp_email,  # Unique temporary email
                    hashed_password="temp",  # Temporary, will be updated
                    role=UserRole.STUDENT
                )
                users_to_create.append((user, user_data))
            
            # Step 2: Bulk add all users to session
            for user, _ in users_to_create:
                db.add(user)
            
            # Step 3: Flush to get all public_ids at once (single DB operation)
            flush_start = datetime.now()
            await db.flush()
            flush_time = (datetime.now() - flush_start).total_seconds()
            logger.debug(f"User flush completed in {flush_time:.3f}s, got {len(users_to_create)} public_ids")
            
            # Step 4: Update users with temporal credentials and prepare profiles
            profile_prep_start = datetime.now()
            profiles_to_create = []
            for user, user_data in users_to_create:
                # Generate temporal credentials using public_id
                temporal_email = f"{user.public_id}@tmp.giaoducthanglong.com"
                temporal_password = f"{user.public_id}@giaoducthanglong"
                
                # Update user with temporal credentials
                user.email = temporal_email
                user.hashed_password = get_password_hash(temporal_password)
                
                # Create profile object
                profile = UserProfile(
                    user_id=user.id,
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    date_of_birth=user_data['date_of_birth'],
                    current_school=user_data['current_school'],
                    current_grade=user_data['current_grade'],
                    default_discount_percentage=user_data['default_discount_percentage']
                )
                profiles_to_create.append((profile, user, user_data, temporal_email, temporal_password))
            
            profile_prep_time = (datetime.now() - profile_prep_start).total_seconds()
            logger.debug(f"Profile preparation completed in {profile_prep_time:.3f}s")
            
            # Step 5: Bulk add all profiles to session
            for profile, _, _, _, _ in profiles_to_create:
                db.add(profile)
            
            # Step 6: Single commit for all users and profiles (single DB transaction)
            commit_start = datetime.now()
            await db.commit()
            commit_time = (datetime.now() - commit_start).total_seconds()
            logger.debug(f"Database commit completed in {commit_time:.3f}s")
            
            # Step 7: Prepare response data
            for profile, user, user_data, temporal_email, temporal_password in profiles_to_create:
                created_users.append({
                    'user': user,
                    'profile': profile,
                    'email': temporal_email,
                    'password': temporal_password,
                    'row': user_data['row_num']
                })
            
            db_time = (datetime.now() - db_start).total_seconds()
            logger.debug(f"Database operations completed in {db_time:.3f}s: {len(created_users)} users created")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating user batch: {e}", exc_info=True)
            # Move all valid users to failed rows
            for user_data in valid_user_data:
                failed_rows.append({
                    'row': user_data['row_num'],
                    'data': user_data['row_data'],
                    'error': f'Batch creation failed: {str(e)}'
                })
            created_users = []
    
    total_time = (datetime.now() - validation_start).total_seconds()
    logger.debug(f"Batch processing completed in {total_time:.3f}s: {len(created_users)} created, {len(failed_rows)} failed")
    
    return created_users, failed_rows


async def update_user(
    db: AsyncSession,
    user_id: UUID,
    email: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[UserRole] = None,
    need_change_email: Optional[bool] = None,
    need_change_password: Optional[bool] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    current_school: Optional[str] = None,
    current_grade: Optional[str] = None,
    default_discount_percentage: Optional[float] = None
) -> Optional[User]:
    """Update user information and profile (partial update).
    
    Args:
        user_id: User ID to update
        email: New email address (optional)
        password: New password (optional)
        role: New role (optional)
        need_change_email: Flag to require email change (optional)
        need_change_password: Flag to require password change (optional)
        first_name: New first name (optional)
        last_name: New last name (optional)
        date_of_birth: New date of birth (optional)
        current_school: New current school (optional)
        current_grade: New current grade (optional)
        default_discount_percentage: New default discount percentage (optional)
    
    Returns:
        Updated User if successful, None otherwise
    """
    try:
        # Get user with profile
        user = await get_user_by_id(db, user_id)
        if not user:
            return None
        
        # Update user fields if provided
        if email is not None:
            # Check if email already exists
            existing_user = await get_user_by_email(db, email)
            if existing_user and existing_user.id != user_id:
                return None  # Email already exists
            user.email = email
        
        if password is not None:
            user.hashed_password = get_password_hash(password)
        
        if role is not None:
            user.role = role
        
        if need_change_email is not None:
            user.need_change_email = need_change_email
        
        if need_change_password is not None:
            user.need_change_password = need_change_password
        
        # Update or create profile if any profile fields are provided
        profile_fields = [
            first_name, last_name, date_of_birth, 
            current_school, current_grade, default_discount_percentage
        ]
        
        if any(field is not None for field in profile_fields):
            if not user.profile:
                # Create new profile
                from app.models.user_profile import UserProfile
                user.profile = UserProfile(user_id=user_id)
                db.add(user.profile)
            
            # Update profile fields
            if first_name is not None:
                user.profile.first_name = first_name
            if last_name is not None:
                user.profile.last_name = last_name
            if date_of_birth is not None:
                user.profile.date_of_birth = date_of_birth
            if current_school is not None:
                user.profile.current_school = current_school
            if current_grade is not None:
                user.profile.current_grade = current_grade
            if default_discount_percentage is not None:
                user.profile.default_discount_percentage = default_discount_percentage
        
        await db.commit()
        await db.refresh(user)
        await db.refresh(user.profile) if user.profile else None
        return user
        
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Error updating user: {e}", exc_info=True)
        return None
