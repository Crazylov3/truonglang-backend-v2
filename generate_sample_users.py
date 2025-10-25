#!/usr/bin/env python3
"""
Script to generate 100 sample users for bulk temporal user creation.
This creates a CSV file that can be uploaded via the /api/v1/users/temporal/bulk endpoint.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

# Sample data for generating realistic user profiles
FIRST_NAMES = [
    "An", "Binh", "Chi", "Duc", "Em", "Giang", "Hoa", "Khanh", "Linh", "Minh",
    "Nam", "Oanh", "Phong", "Quang", "Sang", "Thu", "Uyen", "Viet", "Xuan", "Yen",
    "Alex", "Brian", "Catherine", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack",
    "Kelly", "Liam", "Maya", "Noah", "Olivia", "Paul", "Quinn", "Rachel", "Sam", "Tina"
]

LAST_NAMES = [
    "Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Vo", "Dang", "Bui", "Do",
    "Ngo", "Duong", "Ly", "Dinh", "Phan", "Truong", "Phung", "Ho", "Dong", "Dang",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]

SCHOOLS = [
    "Harvard University", "MIT", "Stanford University", "University of California", "Yale University",
    "Princeton University", "Columbia University", "University of Chicago", "Duke University", "Northwestern University",
    "Truong THPT Nguyen Hue", "Truong THPT Le Quy Don", "Truong THPT Tran Phu", "Truong THPT Nguyen Du",
    "Truong THPT Le Loi", "Truong THPT Quang Trung", "Truong THPT Hai Ba Trung", "Truong THPT Ly Tu Trong",
    "Truong THPT Nguyen Trai", "Truong THPT Vo Thi Sau"
]

GRADES = ["9", "10", "11", "12", "Freshman", "Sophomore", "Junior", "Senior"]

def generate_random_date_of_birth():
    """Generate a random date of birth for students (ages 14-18)."""
    start_date = date.today() - timedelta(days=18*365)  # 18 years ago
    end_date = date.today() - timedelta(days=14*365)    # 14 years ago
    random_days = random.randint(0, (end_date - start_date).days)
    return start_date + timedelta(days=random_days)

def generate_sample_users(num_users=100):
    """Generate sample user data."""
    users = []
    
    for i in range(num_users):
        # Generate random names
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        
        # Generate date of birth (80% chance to have one)
        date_of_birth = None
        if random.random() < 0.8:
            date_of_birth = generate_random_date_of_birth()
        
        # Generate school (70% chance to have one)
        current_school = None
        if random.random() < 0.7:
            current_school = random.choice(SCHOOLS)
        
        # Generate grade (60% chance to have one)
        current_grade = None
        if random.random() < 0.6:
            current_grade = random.choice(GRADES)
        
        # Generate discount percentage (0-50%)
        default_discount_percentage = round(random.uniform(0, 50), 1)
        
        user = {
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': date_of_birth.strftime('%Y-%m-%d') if date_of_birth else '',
            'current_school': current_school or '',
            'current_grade': current_grade or '',
            'default_discount_percentage': default_discount_percentage
        }
        
        users.append(user)
    
    return users

def save_to_csv(users, filename='sample_users.csv'):
    """Save users to CSV file."""
    if not users:
        print("No users to save.")
        return
    
    # Get the fieldnames from the first user
    fieldnames = users[0].keys()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)
    
    print(f"✅ Generated {len(users)} sample users and saved to '{filename}'")
    print(f"📁 File location: {Path(filename).absolute()}")

def main():
    """Main function to generate and save sample users."""
    print("🚀 Generating 100 sample users for bulk temporal user creation...")
    
    # Generate users
    users = generate_sample_users(3000)
    
    # Save to CSV
    save_to_csv(users)
    
    print("\n📋 CSV Format:")
    print("first_name,last_name,date_of_birth,current_school,current_grade,default_discount_percentage")
    print("\n📝 Sample rows:")
    for i, user in enumerate(users[:3]):  # Show first 3 rows
        print(f"{user['first_name']},{user['last_name']},{user['date_of_birth']},{user['current_school']},{user['current_grade']},{user['default_discount_percentage']}")
    
    print(f"\n🔗 You can now upload this CSV file to:")
    print("   POST /api/v1/users/temporal/bulk")
    print("\n📊 Statistics:")
    print(f"   - Total users: {len(users)}")
    print(f"   - Users with DOB: {sum(1 for u in users if u['date_of_birth'])}")
    print(f"   - Users with school: {sum(1 for u in users if u['current_school'])}")
    print(f"   - Users with grade: {sum(1 for u in users if u['current_grade'])}")
    print(f"   - Average discount: {sum(u['default_discount_percentage'] for u in users) / len(users):.1f}%")

if __name__ == "__main__":
    main()
