from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import jwt
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import uuid
import os
from dotenv import load_dotenv
import json
import pandas as pd
import logging
import re

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Board Management System API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme
security = HTTPBearer()

# MongoDB configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "board_management_db")

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class BoardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_path: str  # CDN URL for the board image
    category: Optional[str] = "main"

class BoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_path: Optional[str] = None
    category: Optional[str] = None

class BoardResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    image_path: str
    category: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    has_fmeca: bool
    has_coverage: bool
    has_fmeca_db: bool
    has_coverage_db: bool
    has_image: bool
    last_updated: Optional[datetime]

class ExcelUploadResponse(BaseModel):
    message: str
    board_id: str
    file_type: str
    record_count: Optional[int] = None
    version: Optional[str] = None

class StatusResponse(BaseModel):
    fmeca_exists: bool = False
    coverage_exists: bool = False
    fmeca_in_db: bool = False
    coverage_in_db: bool = False
    has_image: bool = False
    fmeca_info: Optional[Dict[str, Any]] = None
    coverage_info: Optional[Dict[str, Any]] = None

# Utility Functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(token_data: dict = Depends(verify_token)):
    user = await db.users.find_one({"username": token_data["username"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Authentication Endpoints
@app.post("/register", response_model=dict)
async def register(user: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash password
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create user document
    user_doc = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password.decode('utf-8'),
        "role": user.role,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert into database
    result = await db.users.insert_one(user_doc)
    
    return {"message": "User created successfully", "user_id": str(result.inserted_id)}

@app.post("/login", response_model=Token)
async def login(user: UserLogin):
    # Find user
    db_user = await db.users.find_one({"username": user.username})
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not bcrypt.checkpw(user.password.encode('utf-8'), db_user["hashed_password"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    access_token = create_access_token(
        data={"sub": db_user["username"], "role": db_user["role"]}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Board Management Endpoints
@app.get("/boards", response_model=List[BoardResponse])
async def get_boards(current_user: dict = Depends(get_current_user)):
    """Get all boards"""
    boards_cursor = db.boards.find({}).sort("created_at", -1)
    boards = await boards_cursor.to_list(length=None)
    
    formatted_boards = []
    for board in boards:
        formatted_boards.append({
            "id": str(board["_id"]),
            "name": board.get("name", ""),
            "description": board.get("description"),
            "image_path": board.get("image_path", ""),
            "category": board.get("category", "main"),
            "created_by": board.get("created_by"),
            "created_at": board.get("created_at", datetime.utcnow()),
            "updated_at": board.get("updated_at", datetime.utcnow()),
            "has_fmeca": board.get("has_fmeca", False),
            "has_coverage": board.get("has_coverage", False),
            "has_fmeca_db": board.get("has_fmeca_db", False),
            "has_coverage_db": board.get("has_coverage_db", False),
            "has_image": board.get("has_image", False),
            "last_updated": board.get("last_updated")
        })
    
    return formatted_boards

@app.post("/boards", response_model=BoardResponse)
async def create_board(
    board: BoardCreate,
    current_user: dict = Depends(get_current_admin)
):
    """Create a new board with CDN image path"""
    
    # Validate image URL (basic check)
    if not board.image_path.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=400, 
            detail="Image path must be a valid URL starting with http:// or https://"
        )
    
    # Check if board with same name already exists
    existing_board = await db.boards.find_one({"name": board.name})
    if existing_board:
        raise HTTPException(
            status_code=400,
            detail=f"Board with name '{board.name}' already exists"
        )
    
    try:
        # Create board document
        board_doc = {
            "_id": str(uuid.uuid4()),
            "name": board.name,
            "description": board.description,
            "image_path": board.image_path,
            "category": board.category,
            "created_by": current_user.get("username"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "has_fmeca": False,
            "has_coverage": False,
            "has_fmeca_db": False,
            "has_coverage_db": False,
            "has_image": True,  # Since we're adding with image
            "last_updated": datetime.utcnow()
        }
        
        # Insert into MongoDB
        result = await db.boards.insert_one(board_doc)
        
        if result.inserted_id:
            # Return the created board
            return {
                "id": board_doc["_id"],
                "name": board_doc["name"],
                "description": board_doc["description"],
                "image_path": board_doc["image_path"],
                "category": board_doc["category"],
                "created_by": board_doc["created_by"],
                "created_at": board_doc["created_at"],
                "updated_at": board_doc["updated_at"],
                "has_fmeca": board_doc["has_fmeca"],
                "has_coverage": board_doc["has_coverage"],
                "has_fmeca_db": board_doc["has_fmeca_db"],
                "has_coverage_db": board_doc["has_coverage_db"],
                "has_image": board_doc["has_image"],
                "last_updated": board_doc["last_updated"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create board")
            
    except Exception as e:
        logger.error(f"Error creating board: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating board: {str(e)}")

@app.get("/board/{board_id}", response_model=BoardResponse)
async def get_board(board_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific board by ID"""
    board = await db.boards.find_one({"_id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    return {
        "id": str(board["_id"]),
        "name": board.get("name", ""),
        "description": board.get("description"),
        "image_path": board.get("image_path", ""),
        "category": board.get("category", "main"),
        "created_by": board.get("created_by"),
        "created_at": board.get("created_at", datetime.utcnow()),
        "updated_at": board.get("updated_at", datetime.utcnow()),
        "has_fmeca": board.get("has_fmeca", False),
        "has_coverage": board.get("has_coverage", False),
        "has_fmeca_db": board.get("has_fmeca_db", False),
        "has_coverage_db": board.get("has_coverage_db", False),
        "has_image": board.get("has_image", False),
        "last_updated": board.get("last_updated")
    }

@app.put("/board/{board_id}", response_model=BoardResponse)
async def update_board(
    board_id: str,
    board_update: BoardUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """Update board information"""
    
    # Find the board
    board = await db.boards.find_one({"_id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Prepare update data
    update_data = {"updated_at": datetime.utcnow()}
    
    if board_update.name is not None:
        update_data["name"] = board_update.name
    if board_update.description is not None:
        update_data["description"] = board_update.description
    if board_update.image_path is not None:
        # Validate image URL
        if not board_update.image_path.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400, 
                detail="Image path must be a valid URL starting with http:// or https://"
            )
        update_data["image_path"] = board_update.image_path
        update_data["has_image"] = True
    if board_update.category is not None:
        update_data["category"] = board_update.category
    
    # Update the board
    await db.boards.update_one(
        {"_id": board_id},
        {"$set": update_data}
    )
    
    # Get updated board
    updated_board = await db.boards.find_one({"_id": board_id})
    
    return {
        "id": str(updated_board["_id"]),
        "name": updated_board.get("name", ""),
        "description": updated_board.get("description"),
        "image_path": updated_board.get("image_path", ""),
        "category": updated_board.get("category", "main"),
        "created_by": updated_board.get("created_by"),
        "created_at": updated_board.get("created_at", datetime.utcnow()),
        "updated_at": updated_board.get("updated_at", datetime.utcnow()),
        "has_fmeca": updated_board.get("has_fmeca", False),
        "has_coverage": updated_board.get("has_coverage", False),
        "has_fmeca_db": updated_board.get("has_fmeca_db", False),
        "has_coverage_db": updated_board.get("has_coverage_db", False),
        "has_image": updated_board.get("has_image", False),
        "last_updated": updated_board.get("last_updated")
    }

@app.delete("/board/{board_id}")
async def delete_board(
    board_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a board"""
    
    # Find the board
    board = await db.boards.find_one({"_id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Delete the board
    result = await db.boards.delete_one({"_id": board_id})
    
    if result.deleted_count == 1:
        # Also delete associated data
        await db.fmeca_data.delete_many({"board_id": board_id})
        await db.coverage_data.delete_many({"board_id": board_id})
        
        return {"message": f"Board '{board.get('name')}' deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete board")

# File Status Endpoints
@app.get("/board/{board_id}/files", response_model=StatusResponse)
async def get_board_files_status(board_id: str, current_user: dict = Depends(get_current_user)):
    """Get file status for a board"""
    
    # Find the board
    board = await db.boards.find_one({"_id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Get FMECA data from MongoDB
    fmeca_data = await db.fmeca_data.find_one({"board_id": board_id})
    coverage_data = await db.coverage_data.find_one({"board_id": board_id})
    
    # Prepare response
    response = StatusResponse(
        fmeca_exists=board.get("has_fmeca", False),
        coverage_exists=board.get("has_coverage", False),
        fmeca_in_db=board.get("has_fmeca_db", False),
        coverage_in_db=board.get("has_coverage_db", False),
        has_image=board.get("has_image", False)
    )
    
    # Add FMECA info if exists
    if fmeca_data:
        response.fmeca_info = {
            "version": fmeca_data.get("version", "1.0"),
            "record_count": fmeca_data.get("record_count", 0),
            "upload_date": fmeca_data.get("upload_date"),
            "uploaded_by": fmeca_data.get("uploaded_by")
        }
    
    # Add Coverage info if exists
    if coverage_data:
        response.coverage_info = {
            "version": coverage_data.get("version", "1.0"),
            "record_count": coverage_data.get("record_count", 0),
            "upload_date": coverage_data.get("upload_date"),
            "uploaded_by": coverage_data.get("uploaded_by")
        }
    
    return response

@app.get("/board/{board_id}/db-status", response_model=Dict[str, Any])
async def get_board_db_status(board_id: str, current_user: dict = Depends(get_current_user)):
    """Get database status for a board"""
    
    # Find the board
    board = await db.boards.find_one({"_id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Get counts from MongoDB
    fmeca_count = await db.fmeca_data.count_documents({"board_id": board_id})
    coverage_count = await db.coverage_data.count_documents({"board_id": board_id})
    
    # Get latest FMECA and coverage data
    latest_fmeca = await db.fmeca_data.find_one(
        {"board_id": board_id},
        sort=[("upload_date", -1)]
    )
    
    latest_coverage = await db.coverage_data.find_one(
        {"board_id": board_id},
        sort=[("upload_date", -1)]
    )
    
    return {
        "fmeca_in_db": fmeca_count > 0,
        "coverage_in_db": coverage_count > 0,
        "fmeca_count": fmeca_count,
        "coverage_count": coverage_count,
        "fmeca_info": {
            "version": latest_fmeca.get("version", "1.0") if latest_fmeca else None,
            "record_count": latest_fmeca.get("record_count", 0) if latest_fmeca else 0,
            "upload_date": latest_fmeca.get("upload_date") if latest_fmeca else None,
            "uploaded_by": latest_fmeca.get("uploaded_by") if latest_fmeca else None
        } if latest_fmeca else None,
        "coverage_info": {
            "version": latest_coverage.get("version", "1.0") if latest_coverage else None,
            "record_count": latest_coverage.get("record_count", 0) if latest_coverage else 0,
            "upload_date": latest_coverage.get("upload_date") if latest_coverage else None,
            "uploaded_by": latest_coverage.get("uploaded_by") if latest_coverage else None
        } if latest_coverage else None
    }

# File Upload Endpoints
@app.post("/upload/board/{board_id}/excel-to-db", response_model=ExcelUploadResponse)
async def upload_excel_to_db(
    board_id: str,
    file: UploadFile = File(...),
    file_type: str = Form(...),
    current_user: dict = Depends(get_current_admin)
):
    """Upload Excel file to MongoDB"""
    
    # Validate file type
    if file_type not in ["fmeca", "coverage", "image"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Must be 'fmeca', 'coverage', or 'image'")
    
    # Find the board
    board = await db.boards.find_one({"_id": board_id})
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    
    try:
        if file_type == "image":
            # Handle image upload (store metadata only, actual image is on CDN)
            # For now, we just update the board's image status
            await db.boards.update_one(
                {"_id": board_id},
                {"$set": {
                    "has_image": True,
                    "last_updated": datetime.utcnow()
                }}
            )
            
            return ExcelUploadResponse(
                message="Image upload processed successfully",
                board_id=board_id,
                file_type=file_type
            )
        
        else:
            # Read Excel file
            contents = await file.read()
            df = pd.read_excel(contents)
            
            # Convert to JSON
            records = df.to_dict(orient='records')
            
            # Create data document
            data_doc = {
                "board_id": board_id,
                "file_type": file_type,
                "version": "1.0",  # You might want to implement versioning
                "record_count": len(records),
                "data": records,
                "uploaded_by": current_user.get("username"),
                "upload_date": datetime.utcnow(),
                "filename": file.filename
            }
            
            # Insert into appropriate collection
            if file_type == "fmeca":
                collection = db.fmeca_data
                update_field = "has_fmeca_db"
            else:  # coverage
                collection = db.coverage_data
                update_field = "has_coverage_db"
            
            # Insert data
            result = await collection.insert_one(data_doc)
            
            # Update board status
            await db.boards.update_one(
                {"_id": board_id},
                {"$set": {
                    update_field: True,
                    "last_updated": datetime.utcnow()
                }}
            )
            
            return ExcelUploadResponse(
                message=f"{file_type.upper()} data uploaded successfully",
                board_id=board_id,
                file_type=file_type,
                record_count=len(records),
                version=data_doc["version"]
            )
            
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

# User Management Endpoints
@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(current_user: dict = Depends(get_current_admin)):
    """Get all users (admin only)"""
    users_cursor = db.users.find({})
    users = await users_cursor.to_list(length=None)
    
    formatted_users = []
    for user in users:
        formatted_users.append({
            "id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        })
    
    return formatted_users

@app.put("/admin/user/{user_id}")
async def update_user_role(
    user_id: str,
    role: str = Form(...),
    current_user: dict = Depends(get_current_admin)
):
    """Update user role (admin only)"""
    
    if role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    
    # Cannot change own role
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"role": role, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 1:
        return {"message": f"User role updated to {role}"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.delete("/admin/user/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Delete user (admin only)"""
    
    # Cannot delete yourself
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"_id": user_id})
    
    if result.deleted_count == 1:
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        await client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Board Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/register",
            "/login",
            "/boards",
            "/upload",
            "/admin/users"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)