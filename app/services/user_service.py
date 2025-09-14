from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from typing import Optional

class UserService:
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def update_user_role(db: Session, user_id: int, new_role: UserRole) -> Optional[User]:
        """Admin-only function to update user role"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = new_role
            db.commit()
            db.refresh(user)
        return user
    
    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100):
        return db.query(User).offset(skip).limit(limit).all()
