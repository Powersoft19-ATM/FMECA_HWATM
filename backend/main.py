from fastapi import FastAPI, Depends, HTTPException, status, Form
from datetime import timedelta
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException, Depends, status, Body, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from jose import JWTError, jwt
import pandas as pd
import numpy as np
import re
import os
from PIL import Image, ImageDraw
import io
import base64
import shutil
from pathlib import Path
import uuid
import json
from enum import Enum
from dotenv import load_dotenv

FRONTEND_URL = os.getenv("FRONTEND_URL") or "http://localhost:3000"

# Import MongoDB authentication module
from auth import (
    authenticate_user, create_access_token, get_user_by_username,
    create_indexes, init_default_users, SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES, UserInDB, UserResponse, Token, TokenData,
    LoginRequest, RegisterRequest, register_user, get_all_users,
    update_user_password, delete_user, get_user_by_id, create_user, UserCreate,
    users_collection, update_user_last_login, update_user, UserUpdate,
    get_users_by_role, search_users, ROLES, db
)

app = FastAPI(title="FMECA-HWATM Integrations API", version="2.0.0")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000","https://fmeca-hwatm-1.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File upload configuration (only for images if needed)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    'excel': ['.xlsx', '.xls'],
    'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# MongoDB collections
excel_files_collection = db.excel_files

# Enum for file types
class FileType(str, Enum):
    FMECA = "fmeca"
    COVERAGE = "coverage"

# Pydantic models
class BoardInfo(BaseModel):
    id: int
    name: str
    image: Optional[str] = None
    has_fmeca: bool = False
    has_coverage: bool = False
    has_image: bool = False
    has_fmeca_db: bool = False  # New field for DB status
    has_coverage_db: bool = False  # New field for DB status

class FilterRequest(BaseModel):
    board_id: int
    filter_type: str

class FMECAData(BaseModel):
    ID: str
    Component: str
    Reference_Designator: str
    RPN: str
    ATM_Coverage: str

class MissingComponent(BaseModel):
    component: str
    atm_coverage: str

class ATMResponse(BaseModel):
    missing_components: List[MissingComponent]
    message: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class UserCreateRequest(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    role: str = "user"
    disabled: bool = False

class FileUploadResponse(BaseModel):
    message: str
    filename: str
    file_size: int

class BoardFileInfo(BaseModel):
    board_id: int
    board_name: str
    fmeca_exists: bool
    coverage_exists: bool
    image_exists: bool
    fmeca_db_exists: bool
    coverage_db_exists: bool

class ExcelUploadRequest(BaseModel):
    file_type: str  # "fmeca" or "coverage"

class ExcelDataResponse(BaseModel):
    id: str
    board_id: int
    board_name: str
    file_type: str
    original_filename: str
    upload_date: datetime
    uploaded_by: str
    version: int
    record_count: int
    data: Dict[str, Any]

# ================ BOARD CONFIGURATION (Only image URLs, no local files) ================
BOARD_CONFIG = {
    1: {
        "name": "IMD", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/09dd149e-eda2-4e75-87a4-a5c0462f3df9/IMD.png"
    },
    2: {
        "name": "SCR", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/44528739-def7-42ce-8c14-5878b0885312/SCR.png"
    },
    3: {
        "name": "PHTR", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/33880cfd-c882-4020-9ce8-b443a4e84842/PHTR.png"
    },
    4: {
        "name": "VSLD", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/4a9f5c1e-ce38-417f-850d-49673132d669/VSLD.png"
    },
    5: {
        "name": "CLBD", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/70caf3ed-bb93-4049-a47c-a26f9fd0a74e/CLBD.png"
    },
    6: {
        "name": "SVMC", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/b704f94b-6aed-469e-8781-0c16517da575/SVMC.png"
    },
    7: {
        "name": "IPSI", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/a842e819-070c-41eb-bf3b-8ef47ad91d13/IPSI.png"
    },
    8: {
        "name": "MPS", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/3de983c7-3d1d-4e9f-ab7f-f4c1bf24d5a3/MPS.png"
    },
    9: {
        "name": "CC", 
        "image_url": "https://2i5aozhtbd.ucarecd.net/c3794c37-c4bb-42c6-8301-4f5d188cbf40/CC.png"
    }
}
# ================ END: BOARD CONFIGURATION ================

# Startup event
@app.on_event("startup")
async def startup_db_client():
    create_indexes()
    init_default_users()
    create_excel_indexes()
    print("✅ MongoDB initialized with default users")
    print("✅ Excel files indexes created")

# Create indexes for excel files collection
def create_excel_indexes():
    excel_files_collection.create_index([("board_id", 1), ("file_type", 1)])
    excel_files_collection.create_index([("upload_date", -1)])
    excel_files_collection.create_index([("board_id", 1), ("file_type", 1), ("version", -1)])
    print("✅ Excel files indexes created")

# Helper functions
def allowed_file(filename: str, file_type: str = 'excel') -> bool:
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    ext = filename.lower().rsplit('.', 1)[1]
    return f'.{ext}' in ALLOWED_EXTENSIONS.get(file_type, [])

def get_file_size_from_bytes(content: bytes) -> int:
    """Get file size from bytes"""
    return len(content)

def create_colored_placeholder(board_name: str, board_id: int) -> Optional[str]:
    """Create a colored placeholder image"""
    try:
        colors = [
            (70, 130, 180), (220, 20, 60), (34, 139, 34),
            (255, 140, 0), (148, 0, 211), (255, 215, 0),
            (0, 128, 128), (128, 0, 128), (210, 105, 30)
        ]
        
        color = colors[board_id - 1] if board_id <= len(colors) else colors[0]
        
        img = Image.new('RGB', (250, 200), color=color)
        draw = ImageDraw.Draw(img)
        
        text = f"{board_name}\nBoard {board_id}"
        draw.text((125, 100), text, fill=(255, 255, 255), anchor="mm", align="center")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"❌ Error creating placeholder: {e}")
        return None

def load_board_image(board_id: int) -> Optional[str]:
    """Load board image from Uploadcare CDN or create placeholder"""
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        return None
    
    board_name = board_config["name"]
    
    # Use Uploadcare URL if available
    if "image_url" in board_config and board_config["image_url"]:
        uploadcare_url = board_config["image_url"]
        print(f"✅ Using Uploadcare image for {board_name}: {uploadcare_url}")
        return uploadcare_url
    
    # Create colored placeholder
    print(f"⚠️ No image found for {board_name}, using placeholder")
    return create_colored_placeholder(board_name, board_id)

def check_board_files(board_id: int) -> dict:
    """Check what files exist for a board in database only"""
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        return {"fmeca_exists": False, "coverage_exists": False, "image_exists": False,
                "fmeca_db_exists": False, "coverage_db_exists": False}
    
    board_name = board_config["name"]
    
    # Check if data exists in database only (no local files)
    fmeca_db_exists = excel_files_collection.count_documents({
        "board_id": board_id, 
        "file_type": "fmeca"
    }) > 0
    
    coverage_db_exists = excel_files_collection.count_documents({
        "board_id": board_id, 
        "file_type": "coverage"
    }) > 0
    
    # Check for image
    image_exists = False
    if "image_url" in board_config and board_config["image_url"]:
        image_exists = True
    
    return {
        "fmeca_exists": fmeca_db_exists,  # Now refers to DB only
        "coverage_exists": coverage_db_exists,  # Now refers to DB only
        "image_exists": image_exists,
        "fmeca_db_exists": fmeca_db_exists,
        "coverage_db_exists": coverage_db_exists
    }

def load_main_data(board_id: int) -> pd.DataFrame:
    """Load FMECA data for specific board - Only from database"""
    try:
        # Load from database only
        df_from_db = load_main_data_from_db(board_id)
        if not df_from_db.empty:
            return df_from_db
        
        print(f"❌ No FMECA data found in database for board {board_id}")
        return pd.DataFrame()
        
    except Exception as e:
        print(f"❌ Error loading FMECA data: {e}")
        return pd.DataFrame()

def load_main_data_from_db(board_id: int) -> pd.DataFrame:
    """Load FMECA data from MongoDB"""
    try:
        # Get latest FMECA data from DB
        record = excel_files_collection.find_one(
            {"board_id": board_id, "file_type": "fmeca"},
            sort=[("upload_date", -1)]
        )
        
        if not record:
            print(f"⚠️ No FMECA data in DB for board {board_id}")
            return pd.DataFrame()
        
        data = record["data"]
        
        # Convert back to DataFrame
        if isinstance(data, dict) and "data" in data and "columns" in data:
            df = pd.DataFrame(data["data"], columns=data["columns"])
        else:
            df = pd.DataFrame(data)
        
        print(f"✅ FMECA data loaded from DB: {len(df)} rows")
        return df
        
    except Exception as e:
        print(f"❌ Error loading from DB: {e}")
        return pd.DataFrame()

def load_reference_data(board_id: int) -> pd.DataFrame:
    """Load coverage data for specific board - Only from database"""
    try:
        # Load from database only
        df_from_db = load_reference_data_from_db(board_id)
        if not df_from_db.empty:
            return df_from_db
        
        print(f"❌ No coverage data found in database for board {board_id}")
        return pd.DataFrame()
        
    except Exception as e:
        print(f"❌ Error loading coverage data: {e}")
        return pd.DataFrame()

def load_reference_data_from_db(board_id: int) -> pd.DataFrame:
    """Load coverage data from MongoDB"""
    try:
        # Get latest coverage data from DB
        record = excel_files_collection.find_one(
            {"board_id": board_id, "file_type": "coverage"},
            sort=[("upload_date", -1)]
        )
        
        if not record:
            print(f"⚠️ No coverage data in DB for board {board_id}")
            return pd.DataFrame()
        
        data = record["data"]
        
        # Convert back to DataFrame
        if isinstance(data, dict) and "data" in data and "columns" in data:
            df = pd.DataFrame(data["data"], columns=data["columns"])
        else:
            df = pd.DataFrame(data)
        
        print(f"✅ Coverage data loaded from DB: {len(df)} rows")
        return df
        
    except Exception as e:
        print(f"❌ Error loading from DB: {e}")
        return pd.DataFrame()

def extract_designators(text: str) -> set:
    if pd.isna(text) or text == '':
        return set()
    
    text = str(text).upper().strip()
    designators = set()
    
    parentheses_matches = re.findall(r'\(([A-Z]{1,3}\d{1,4}[A-Z]?\d?)\)', text)
    designators.update(parentheses_matches)
    
    standalone_matches = re.findall(r'\b([A-Z]{1,10}\d{1,4}[A-Z]?\d?)\b', text)
    designators.update(standalone_matches)
    
    complex_matches = re.findall(r'[A-Z]{1,10}\s*\d{1,4}[A-Z]?\d?', text.replace(' ', ''))
    designators.update(complex_matches)
    
    return designators

def extract_complete_designators(text: str) -> set:
    if pd.isna(text) or text == '':
        return set()
    
    text = str(text).upper().strip()
    designators = set()
    
    pattern = r'\b([A-Z]{1,10}\d{1,4}(?:[A-Z]\d?)?)\b'
    matches = re.findall(pattern, text)
    designators.update(matches)
    
    parentheses_matches = re.findall(r'\(([A-Z]{1,10}\d{1,4}(?:[A-Z]\d?)?)\)', text)
    designators.update(parentheses_matches)
    
    return designators

# Dependency functions
def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_admin_user(current_user: UserInDB = Depends(get_current_active_user)) -> UserInDB:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/token", response_model=Token)
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login endpoint - returns JWT token"""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    update_user_last_login(user.username)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_model=UserResponse)
async def register_new_user(user_data: RegisterRequest):
    """Register a new user"""
    try:
        user = register_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.get("/verify-token", response_model=UserResponse)
async def verify_token(current_user: UserInDB = Depends(get_current_active_user)):
    """Verify if token is valid and return user info"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        disabled=current_user.disabled,
        role=current_user.role,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login
    )

@app.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Change user's password"""
    from auth import verify_password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    update_user_password(current_user.username, password_data.new_password)
    return {"message": "Password updated successfully"}

# ==================== USER MANAGEMENT ENDPOINTS ====================

@app.get("/admin/users", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
    admin: UserInDB = Depends(get_admin_user)
):
    """Get all users with optional filtering (admin only)"""
    if search:
        users = search_users(search, skip, limit)
    elif role:
        users = get_users_by_role(role, skip, limit)
    else:
        users = get_all_users(skip, limit)
    return users

@app.get("/admin/users/{username}", response_model=UserResponse)
async def get_user(
    username: str,
    admin: UserInDB = Depends(get_admin_user)
):
    """Get user by username (admin only)"""
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login
    )

@app.post("/admin/users", response_model=UserResponse)
async def create_new_user(
    user_data: UserCreateRequest,
    admin: UserInDB = Depends(get_admin_user)
):
    """Create a new user (admin only)"""
    try:
        user_create = UserCreate(**user_data.dict())
        user = create_user(user_create)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@app.put("/admin/users/{username}")
async def update_user_info(
    username: str,
    user_update: UserUpdate,
    admin: UserInDB = Depends(get_admin_user)
):
    """Update user information (admin only)"""
    try:
        updated_user = update_user(username, user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            full_name=updated_user.full_name,
            disabled=updated_user.disabled,
            role=updated_user.role,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            last_login=updated_user.last_login
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@app.put("/admin/users/{username}/disable")
async def disable_user(
    username: str,
    admin: UserInDB = Depends(get_admin_user)
):
    """Disable a user (admin only)"""
    if username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_collection.update_one(
        {"username": username},
        {"$set": {"disabled": True, "updated_at": datetime.utcnow()}}
    )
    return {"message": f"User {username} disabled"}

@app.put("/admin/users/{username}/enable")
async def enable_user(
    username: str,
    admin: UserInDB = Depends(get_admin_user)
):
    """Enable a user (admin only)"""
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_collection.update_one(
        {"username": username},
        {"$set": {"disabled": False, "updated_at": datetime.utcnow()}}
    )
    return {"message": f"User {username} enabled"}

@app.delete("/admin/users/{username}")
async def delete_user_account(
    username: str,
    admin: UserInDB = Depends(get_admin_user)
):
    """Delete a user (admin only)"""
    if username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    success = delete_user(username)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {username} deleted"}

@app.get("/admin/roles")
async def get_available_roles(admin: UserInDB = Depends(get_admin_user)):
    """Get list of available roles (admin only)"""
    return {"roles": ROLES}

# ==================== EXCEL TO DATABASE UPLOAD ENDPOINTS ====================

@app.post("/upload/board/{board_id}/excel-to-db")
async def upload_excel_to_database(
    board_id: int,
    file_type: str = Form(...),  # "fmeca" or "coverage"
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Upload Excel file and store its data in MongoDB as JSON
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can upload files")
    
    if not allowed_file(file.filename, 'excel'):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed (.xlsx, .xls)")
    
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        raise HTTPException(status_code=404, detail="Board not found")
    
    if file_type not in ["fmeca", "coverage"]:
        raise HTTPException(status_code=400, detail="file_type must be 'fmeca' or 'coverage'")
    
    try:
        # Read Excel file
        contents = await file.read()
        excel_bytes = io.BytesIO(contents)
        
        # Try different sheets based on file type
        if file_type == "fmeca":
            sheet_names = ['DFMECA', 'Sheet1', 'FMECA', 'Data']
        else:  # coverage
            sheet_names = ['iiGD board', 'Sheet1', 'Coverage', 'Data', 'ATM']
        
        df = None
        
        for sheet in sheet_names:
            try:
                df = pd.read_excel(excel_bytes, sheet_name=sheet)
                print(f"✅ Loaded from sheet: {sheet}")
                break
            except:
                continue
        
        if df is None:
            excel_bytes.seek(0)  # Reset pointer
            df = pd.read_excel(excel_bytes)
            print("✅ Loaded from first available sheet")
        
        # Fill NaN values
        df = df.ffill()
        
        # Convert DataFrame to structured dictionary
        data_dict = {
            "columns": df.columns.tolist(),
            "data": df.replace({pd.NaT: None, np.nan: None}).to_dict(orient='records'),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
            "shape": df.shape
        }
        
        # Get version number (increment from previous version)
        latest_version = excel_files_collection.find_one(
            {"board_id": board_id, "file_type": file_type},
            sort=[("version", -1)]
        )
        
        version = 1
        if latest_version and "version" in latest_version:
            version = latest_version["version"] + 1
        
        # Generate unique ID
        file_id = str(uuid.uuid4())
        
        # Prepare document for MongoDB
        excel_record = {
            "_id": file_id,
            "board_id": board_id,
            "board_name": board_config["name"],
            "file_type": file_type,
            "original_filename": file.filename,
            "stored_filename": f"{file_id}.json",
            "file_size": len(contents),
            "data": data_dict,
            "upload_date": datetime.utcnow(),
            "uploaded_by": current_user.username,
            "version": version
        }
        
        # Save to MongoDB
        result = excel_files_collection.insert_one(excel_record)
        
        return {
            "message": "Excel file uploaded and stored in database successfully",
            "file_id": file_id,
            "record_count": len(data_dict["data"]),
            "stored_size": len(contents),
            "version": version,
            "board_id": board_id,
            "board_name": board_config["name"]
        }
        
    except Exception as e:
        print(f"❌ Error uploading Excel to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process Excel file: {str(e)}")

@app.get("/get/excel-data/{board_id}")
async def get_excel_data_from_db(
    board_id: int,
    file_type: Optional[str] = None,  # Optional: "fmeca" or "coverage"
    version: Optional[int] = None,    # Optional: specific version
    limit: int = 100,                  # Limit records
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Get Excel data from MongoDB for a specific board
    """
    query = {"board_id": board_id}
    if file_type:
        if file_type not in ["fmeca", "coverage"]:
            raise HTTPException(status_code=400, detail="file_type must be 'fmeca' or 'coverage'")
        query["file_type"] = file_type
    if version:
        query["version"] = version
    
    # Get latest version if not specified
    sort_order = [("upload_date", -1)]
    
    records = list(excel_files_collection.find(query).sort(sort_order).limit(limit))
    
    if not records:
        raise HTTPException(status_code=404, detail="No Excel data found for this board")
    
    # Convert to response format
    response_data = []
    for record in records:
        # Limit data size for response
        data = record["data"]
        record_count = len(data["data"]) if isinstance(data, dict) and "data" in data else len(data)
        
        response_data.append({
            "id": record["_id"],
            "board_id": record["board_id"],
            "board_name": record["board_name"],
            "file_type": record["file_type"],
            "original_filename": record["original_filename"],
            "upload_date": record["upload_date"],
            "uploaded_by": record["uploaded_by"],
            "version": record.get("version", 1),
            "record_count": record_count,
            "data": data  # The actual JSON data
        })
    
    return {
        "count": len(response_data),
        "board_id": board_id,
        "data": response_data
    }

@app.delete("/delete/excel-data/{file_id}")
async def delete_excel_data(
    file_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Delete Excel data from MongoDB (admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete data")
    
    result = excel_files_collection.delete_one({"_id": file_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"message": "Excel data deleted successfully", "file_id": file_id}

@app.get("/board/{board_id}/db-status")
async def get_board_db_status(
    board_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """
    Get database status for a board
    """
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Get latest records for both file types
    fmeca_record = excel_files_collection.find_one(
        {"board_id": board_id, "file_type": "fmeca"},
        sort=[("upload_date", -1)]
    )
    
    coverage_record = excel_files_collection.find_one(
        {"board_id": board_id, "file_type": "coverage"},
        sort=[("upload_date", -1)]
    )
    
    return {
        "board_id": board_id,
        "board_name": board_config["name"],
        "fmeca_in_db": fmeca_record is not None,
        "coverage_in_db": coverage_record is not None,
        "fmeca_info": {
            "upload_date": fmeca_record["upload_date"] if fmeca_record else None,
            "uploaded_by": fmeca_record["uploaded_by"] if fmeca_record else None,
            "version": fmeca_record.get("version", 1) if fmeca_record else None,
            "record_count": len(fmeca_record["data"]["data"]) if fmeca_record and "data" in fmeca_record else None
        } if fmeca_record else None,
        "coverage_info": {
            "upload_date": coverage_record["upload_date"] if coverage_record else None,
            "uploaded_by": coverage_record["uploaded_by"] if coverage_record else None,
            "version": coverage_record.get("version", 1) if coverage_record else None,
            "record_count": len(coverage_record["data"]["data"]) if coverage_record and "data" in coverage_record else None
        } if coverage_record else None
    }

# ==================== FILE UPLOAD ENDPOINTS ====================

@app.post("/upload/board/{board_id}/fmeca")
async def upload_fmeca_file(
    board_id: int,
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Upload FMECA Excel file for a board (to database only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can upload files")
    
    if not allowed_file(file.filename, 'excel'):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed (.xlsx, .xls)")
    
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Use the excel-to-db endpoint logic
    return await upload_excel_to_database(
        board_id=board_id,
        file_type="fmeca",
        file=file,
        current_user=current_user
    )

@app.post("/upload/board/{board_id}/coverage")
async def upload_coverage_file(
    board_id: int,
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Upload coverage Excel file for a board (to database only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can upload files")
    
    if not allowed_file(file.filename, 'excel'):
        raise HTTPException(status_code=400, detail="Only Excel files are allowed (.xlsx, .xls)")
    
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        raise HTTPException(status_code=404, detail="Board not found")
    
    # Use the excel-to-db endpoint logic
    return await upload_excel_to_database(
        board_id=board_id,
        file_type="coverage",
        file=file,
        current_user=current_user
    )

@app.get("/board/{board_id}/files", response_model=BoardFileInfo)
async def get_board_file_info(
    board_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get information about files for a board (database only)"""
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        raise HTTPException(status_code=404, detail="Board not found")
    
    file_info = check_board_files(board_id)
    
    return BoardFileInfo(
        board_id=board_id,
        board_name=board_config["name"],
        fmeca_exists=file_info["fmeca_exists"],
        coverage_exists=file_info["coverage_exists"],
        image_exists=file_info["image_exists"],
        fmeca_db_exists=file_info["fmeca_db_exists"],
        coverage_db_exists=file_info["coverage_db_exists"]
    )

# ==================== BOARD MANAGEMENT ENDPOINTS ====================

@app.get("/", response_model=dict)
async def root():
    """API root endpoint"""
    return {
        "message": "FMECA-HWATM Integrations API",
        "version": "2.0.0",
        "features": ["User Management", "File Upload to Database", "FMECA Analysis", "Database Storage Only"]
    }

@app.get("/boards", response_model=List[BoardInfo])
async def get_boards(current_user: UserInDB = Depends(get_current_active_user)):
    """Get all boards with file status (database only)"""
    print("🎯 /boards API called")
    boards = []
    for board_id, board_config in BOARD_CONFIG.items():
        print(f"🔍 Processing board: {board_config['name']} (ID: {board_id})")
        
        file_info = check_board_files(board_id)
        image_data = load_board_image(board_id)
        
        boards.append(BoardInfo(
            id=board_id, 
            name=board_config["name"], 
            image=image_data,
            has_fmeca=file_info["fmeca_exists"],
            has_coverage=file_info["coverage_exists"],
            has_image=file_info["image_exists"],
            has_fmeca_db=file_info["fmeca_db_exists"],
            has_coverage_db=file_info["coverage_db_exists"]
        ))
    
    print("✅ All boards processed successfully")
    return boards

@app.post("/fmeca-data/{board_id}")
async def get_fmeca_data(
    board_id: int, 
    filter_request: FilterRequest,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get FMECA data for a board with filtering (from database only)"""
    try:
        print(f"📊 FMECA data requested for board {board_id} with filter {filter_request.filter_type}")
        
        df = load_main_data(board_id)
        ref_df = load_reference_data(board_id)
        
        if df.empty:
            return {"data": [], "count": 0, "message": "No FMECA data found in database"}
        
        if ref_df.empty:
            return {"data": [], "count": 0, "message": "No coverage data found in database"}
        
        # Find relevant columns
        id_col = None
        component_col = None
        designator_col = None
        rpn_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'id' in col_lower and not id_col:
                id_col = col
            elif 'component' in col_lower and not component_col:
                component_col = col
            elif 'reference' in col_lower and 'designator' in col_lower and not designator_col:
                designator_col = col
            elif 'rpn' in col_lower and not rpn_col:
                rpn_col = col
        
        if not all([id_col, component_col, designator_col, rpn_col]):
            cols = df.columns.tolist()
            if len(cols) >= 4:
                id_col = cols[0] if not id_col else id_col
                component_col = cols[1] if not component_col else component_col
                designator_col = cols[2] if not designator_col else designator_col
                rpn_col = cols[3] if not rpn_col else rpn_col
        
        print(f"📝 Using columns - ID: {id_col}, Component: {component_col}, Designator: {designator_col}, RPN: {rpn_col}")
        
        selected_columns = [id_col, component_col, designator_col, rpn_col]
        base_df = df[selected_columns].copy()
        
        base_df[rpn_col] = pd.to_numeric(base_df[rpn_col], errors='coerce')
        
        # Apply filters
        if filter_request.filter_type == "red":
            df_filtered = base_df[base_df[rpn_col] >= 70]
        elif filter_request.filter_type == "orange":
            df_filtered = base_df[(base_df[rpn_col] < 70) & (base_df[rpn_col] >= 60)]
        elif filter_request.filter_type == "yellow":
            df_filtered = base_df[(base_df[rpn_col] < 60) & (base_df[rpn_col] >= 50)]
        elif filter_request.filter_type == "green":
            df_filtered = base_df[base_df[rpn_col] < 50]
        elif filter_request.filter_type == "all":
            df_filtered = base_df
        else:
            df_filtered = base_df

        df_filtered = df_filtered.sort_values(by=rpn_col, ascending=False)
        
        df_filtered["ATM Coverage"] = "Not Found"
        
        crd_col = None
        result_col = None
        
        for col in ref_df.columns:
            col_lower = str(col).lower()
            if 'crd' in col_lower and not crd_col:
                crd_col = col
            elif 'result' in col_lower and not result_col:
                result_col = col
        
        if not crd_col or not result_col:
            ref_cols = ref_df.columns.tolist()
            if len(ref_cols) >= 2:
                crd_col = ref_cols[0] if not crd_col else crd_col
                result_col = ref_cols[1] if not result_col else result_col
        
        if crd_col and result_col:
            df_filtered[designator_col] = df_filtered[designator_col].astype(str).str.upper()
            ref_df[crd_col] = ref_df[crd_col].astype(str).str.upper()
            
            for _, row in ref_df.iterrows():
                crd = str(row[crd_col]).strip()
                result_val = str(row[result_col])
                
                crd_designators = extract_complete_designators(crd)
                
                for designator in crd_designators:
                    mask = df_filtered[designator_col].str.contains(re.escape(designator), na=False, regex=True)
                    df_filtered.loc[mask, "ATM Coverage"] = result_val

        result_data = []
        for _, row in df_filtered.iterrows():
            result_data.append({
                "ID": str(row[id_col]),
                "Component": str(row[component_col]),
                "Reference_Designator": str(row[designator_col]),
                "RPN": str(row[rpn_col]),
                "ATM_Coverage": str(row["ATM Coverage"])
            })
        
        return {"data": result_data, "count": len(result_data), "message": f"Found {len(result_data)} records"}
        
    except Exception as e:
        print(f"❌ Error in FMECA data: {e}")
        return {"data": [], "count": 0, "error": str(e)}

@app.get("/atm-check/{board_id}", response_model=ATMResponse)
async def atm_check(
    board_id: int,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Perform ATM check for a board (from database only)"""
    try:
        print(f"🏧 ATM check requested for board {board_id}")
        
        df = load_main_data(board_id)
        ref_df = load_reference_data(board_id)
        
        if df.empty or ref_df.empty:
            return ATMResponse(
                missing_components=[],
                message="No data found in database"
            )
        
        designator_col = None
        for col in df.columns:
            if 'reference' in str(col).lower() and 'designator' in str(col).lower():
                designator_col = col
                break
        
        if not designator_col:
            designator_col = df.columns[2] if len(df.columns) > 2 else df.columns[0]
        
        crd_col = None
        result_col = None
        for col in ref_df.columns:
            col_lower = str(col).lower()
            if 'crd' in col_lower:
                crd_col = col
            elif 'result' in col_lower:
                result_col = col
        
        if not crd_col or not result_col:
            ref_cols = ref_df.columns.tolist()
            if len(ref_cols) >= 2:
                crd_col = ref_cols[0] if not crd_col else crd_col
                result_col = ref_cols[1] if not result_col else result_col
        
        fmeca_designators = set()
        for designator_str in df[designator_col]:
            extracted = extract_designators(designator_str)
            fmeca_designators.update(extracted)
        
        iigd_designators = set()
        for crd_str in ref_df[crd_col]:
            extracted = extract_complete_designators(crd_str)
            iigd_designators.update(extracted)
        
        truly_missing = set()
        for iigd_designator in iigd_designators:
            designator_clean = iigd_designator.upper().strip()
            found = False
            
            for fmeca_designator in fmeca_designators:
                if (designator_clean == fmeca_designator or 
                    f"({designator_clean})" in fmeca_designator or 
                    designator_clean in fmeca_designator.split()):
                    found = True
                    break
            
            if not found:
                truly_missing.add(iigd_designator)
        
        truly_missing = {d for d in truly_missing if d and len(d) > 1 and d not in ['NAN', 'NONE', 'NAT', 'NULL', 'NA']}
        
        missing_components = []
        for missing_designator in sorted(truly_missing):
            result_value = "Not Found"
            for _, row in ref_df.iterrows():
                crd = str(row[crd_col])
                result_val = str(row[result_col])
                crd_designators = extract_complete_designators(crd)
                if missing_designator in crd_designators:
                    result_value = result_val
                    break
            
            missing_components.append(MissingComponent(
                component=missing_designator,
                atm_coverage=result_value
            ))
        
        if missing_components:
            message = f"ATM Check: {len(truly_missing)} values found in coverage but missing in FMECA"
        else:
            message = "🎉 ATM Check: All coverage values are present in FMECA"
        
        return ATMResponse(
            missing_components=missing_components,
            message=message
        )
        
    except Exception as e:
        print(f"❌ Error in ATM check: {e}")
        return ATMResponse(
            missing_components=[],
            message=f"Error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
