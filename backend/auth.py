import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
from pymongo import MongoClient
from bson import ObjectId
# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "fmeca_db")
USERS_COLLECTION = "users"

# Initialize MongoDB client
client = MongoClient(MONGODB_URL)
db = client[DATABASE_NAME]
users_collection = db.users

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Role constants
ROLES = ["admin", "user"]

# Pydantic Models
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: bool = False
    role: str = "user"

    @validator('role')
    def validate_role(cls, v):
        if v not in ROLES:
            raise ValueError(f'Role must be one of: {", ".join(ROLES)}')
        return v

class UserCreate(UserBase):
    password: str

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    role: Optional[str] = None

    @validator('role')
    def validate_role(cls, v):
        if v is not None and v not in ROLES:
            raise ValueError(f'Role must be one of: {", ".join(ROLES)}')
        return v

class UserInDB(UserBase):
    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: str
    role: str = "user"

    @validator('role')
    def validate_role(cls, v):
        if v not in ROLES:
            raise ValueError(f'Role must be one of: {", ".join(ROLES)}')
        return v

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters long')
        return v

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Database operations
def create_indexes():
    """Create database indexes"""
    try:
        users_collection.create_index("username", unique=True)
        users_collection.create_index("email", unique=True, sparse=True)
        users_collection.create_index("created_at")
        users_collection.create_index("role")
        print("✅ Database indexes created successfully")
    except Exception as e:
        print(f"⚠️ Error creating indexes: {e}")

def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get user by ID"""
    try:
        user_data = users_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            user_data["id"] = str(user_data["_id"])
            return UserInDB(**user_data)
    except Exception as e:
        print(f"Error getting user by ID: {e}")
    return None

def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Get user by username"""
    try:
        user_data = users_collection.find_one({"username": username})
        if user_data:
            user_data["id"] = str(user_data["_id"])
            return UserInDB(**user_data)
    except Exception as e:
        print(f"Error getting user by username: {e}")
    return None

def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get user by email"""
    try:
        user_data = users_collection.find_one({"email": email})
        if user_data:
            user_data["id"] = str(user_data["_id"])
            return UserInDB(**user_data)
    except Exception as e:
        print(f"Error getting user by email: {e}")
    return None

def get_users_by_role(role: str, skip: int = 0, limit: int = 100) -> List[UserInDB]:
    """Get users by role"""
    try:
        cursor = users_collection.find({"role": role}).skip(skip).limit(limit)
        users = []
        for user in cursor:
            user["id"] = str(user["_id"])
            users.append(UserInDB(**user))
        return users
    except Exception as e:
        print(f"Error getting users by role: {e}")
        return []

def create_user(user_data: UserCreate) -> UserResponse:
    """Create a new user"""
    # Check if username already exists
    existing_user = get_user_by_username(user_data.username)
    if existing_user:
        raise ValueError(f"Username '{user_data.username}' already exists")
    
    # Check if email already exists
    if user_data.email:
        existing_email = get_user_by_email(user_data.email)
        if existing_email:
            raise ValueError(f"Email '{user_data.email}' already exists")
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user document
    user_dict = user_data.dict(exclude={"password"})
    user_dict.update({
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    try:
        result = users_collection.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        user_dict["id"] = str(result.inserted_id)
        
        return UserResponse(**user_dict)
    except pymongo.errors.DuplicateKeyError as e:
        raise ValueError("Username or email already exists") from e
    except Exception as e:
        raise ValueError(f"Error creating user: {e}") from e

def update_user(username: str, user_update: UserUpdate) -> Optional[UserInDB]:
    """Update user information"""
    try:
        update_data = user_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # If email is being updated, check if it already exists
        if "email" in update_data and update_data["email"]:
            existing_user = get_user_by_email(update_data["email"])
            if existing_user and existing_user.username != username:
                raise ValueError("Email already exists")
        
        result = users_collection.update_one(
            {"username": username},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return get_user_by_username(username)
        return None
    except ValueError as e:
        raise e
    except Exception as e:
        print(f"Error updating user: {e}")
        return None

def update_user_last_login(username: str):
    """Update user's last login timestamp"""
    try:
        users_collection.update_one(
            {"username": username},
            {
                "$set": {
                    "last_login": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
    except Exception as e:
        print(f"Error updating last login: {e}")

def update_user_password(username: str, new_password: str):
    """Update user's password"""
    hashed_password = get_password_hash(new_password)
    try:
        users_collection.update_one(
            {"username": username},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )
    except Exception as e:
        print(f"Error updating password: {e}")

def get_all_users(skip: int = 0, limit: int = 100) -> List[UserInDB]:
    """Get all users (for admin purposes)"""
    try:
        cursor = users_collection.find().skip(skip).limit(limit)
        users = []
        for user in cursor:
            user["id"] = str(user["_id"])
            users.append(UserInDB(**user))
        return users
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []

def delete_user(username: str):
    """Delete a user (for admin purposes)"""
    try:
        result = users_collection.delete_one({"username": username})
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting user: {e}")
        return False

def search_users(search_term: str, skip: int = 0, limit: int = 100) -> List[UserInDB]:
    """Search users by username, email, or full name"""
    try:
        query = {
            "$or": [
                {"username": {"$regex": search_term, "$options": "i"}},
                {"email": {"$regex": search_term, "$options": "i"}},
                {"full_name": {"$regex": search_term, "$options": "i"}}
            ]
        }
        cursor = users_collection.find(query).skip(skip).limit(limit)
        users = []
        for user in cursor:
            user["id"] = str(user["_id"])
            users.append(UserInDB(**user))
        return users
    except Exception as e:
        print(f"Error searching users: {e}")
        return []

# Authentication
def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def register_user(user_data: RegisterRequest) -> UserResponse:
    """Register a new user"""
    user_create = UserCreate(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password=user_data.password,
        disabled=False,
        role=user_data.role
    )
    return create_user(user_create)

# JWT Token creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Initialize default users
def init_default_users():
    """Initialize default users if they don't exist"""
    default_users = [
        {
            "username": "admin",
            "email": "admin@fmeca.com",
            "full_name": "Administrator",
            "password": "admin123",
            "role": "admin",
            "disabled": False
        },
        
        
    ]
    
    for user_data in default_users:
        existing_user = get_user_by_username(user_data["username"])
        if not existing_user:
            try:
                user_create = UserCreate(**user_data)
                create_user(user_create)
                print(f"✅ Created default user: {user_data['username']}")
            except ValueError as e:
                print(f"⚠️ User {user_data['username']} already exists or error: {e}")
            except Exception as e:
                print(f"❌ Error creating user {user_data['username']}: {e}")
        else:
            print(f"✅ User {user_data['username']} already exists")