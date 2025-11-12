#!/usr/bin/env python3
"""
Simple script to create a test user for login testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.security import get_password_hash

def create_test_user():
    db = next(get_db())
    
    # Check if test user already exists
    existing_user = db.query(User).filter(User.email == "test@example.com").first()
    if existing_user:
        print("Test user already exists!")
        print(f"Email: {existing_user.email}")
        print(f"Username: {existing_user.username}")
        return
    
    # Create test user
    test_user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("password123"),
        faculty_id=1,  # Faculty of Computing and Informatics
        program_id=1,  # Bachelor of Science Computer Science
        is_verified=True
    )
    
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    
    print("Test user created successfully!")
    print(f"Email: {test_user.email}")
    print(f"Username: {test_user.username}")
    print("Password: password123")
    print(f"Faculty ID: {test_user.faculty_id}")
    print(f"Program ID: {test_user.program_id}")

if __name__ == "__main__":
    create_test_user()