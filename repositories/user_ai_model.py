from typing import Type, Optional, List
from sqlalchemy.orm import Session
from models.user_ai_model import UserAIModel
from schemas.user_ai_model import UserAIModelCreate, UserAIModelUpdate
from uuid import UUID

class UserAIModelRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_model(self, user_id: UUID, ai_model_id: UUID) -> Optional[UserAIModel]:
        return self.db.query(UserAIModel).filter_by(user_id=user_id, ai_model_id=ai_model_id).first()

    def create(self, user_id: UUID, obj_in: UserAIModelCreate) -> UserAIModel:
        db_obj = UserAIModel(user_id=user_id, **obj_in.dict())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: UserAIModel, obj_in: UserAIModelUpdate) -> UserAIModel:
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, db_obj: UserAIModel):
        self.db.delete(db_obj)
        self.db.commit()

    def get_all_by_user(self, user_id: UUID) -> List[UserAIModel]:
        return self.db.query(UserAIModel).filter_by(user_id=user_id).all()
