from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd
import re
import os
from PIL import Image
import io
import base64
from typing import List, Dict, Any

app = FastAPI(title="FMECA Hardware Integrations API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Board names mapping
BOARD_NAMES = {
    1: "IMD",
    2: "SCR", 
    3: "PHTR",
    4: "VSLD",
    5: "CLBD",
    6: "SVMC",
    7: "IPSI",
    8: "MPS"
}

# Load data functions
def load_main_data():
    df = pd.read_excel('FMECA-iiGD Rev3-Rev4 (P111319).xlsx', sheet_name='DFMECA')
    df = df.ffill()
    return df

def load_reference_data():
    ref_df = pd.read_excel('iiGD Board Coverage Analysis - Rev 1.xlsx', sheet_name='iiGD board')
    return ref_df

# Pydantic models
class BoardInfo(BaseModel):
    id: int
    name: str
    image: str = None

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

# Utility functions (same as original)
def extract_designators(text):
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

def extract_complete_designators(text):
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

def check_designator_in_fmeca(designator, fmeca_designators):
    designator_clean = designator.upper().strip()
    
    if designator_clean in fmeca_designators:
        return True
    
    for fmeca_designator in fmeca_designators:
        if designator_clean == fmeca_designator:
            return True
        if f"({designator_clean})" in fmeca_designator or designator_clean in fmeca_designator.split():
            return True
    
    return False

def find_result_for_designator(designator, ref_df):
    designator_clean = designator.upper().strip()
    
    for _, row in ref_df.iterrows():
        crd = str(row["CRD"])
        result_val = str(row["Result"])
        
        crd_designators = extract_complete_designators(crd)
        
        if designator_clean in crd_designators:
            return result_val
    
    return "Not Found in iiGD"

def load_board_image(board_id):
    board_name = BOARD_NAMES.get(board_id, f"Board {board_id}")
    
    possible_paths = [
        f"boards/{board_name}.png",
        f"boards/{board_name}.jpg", 
        f"boards/{board_name}.jpeg",
        f"boards/{board_name}.PNG",
        f"boards/{board_name}.JPG",
        f"boards/{board_name}.JPEG",
        f"boards/Board {board_id}.png",
        f"boards/Board {board_id}.jpg",
        f"boards/Board {board_id}.jpeg",
        f"boards/Board {board_id}.PNG",
        f"boards/Board {board_id}.JPG",
        f"boards/Board {board_id}.JPEG",
        f"boards/board{board_id}.png",
        f"boards/board{board_id}.jpg",
        f"boards/board{board_id}.jpeg",
    ]
    
    for image_path in possible_paths:
        if os.path.exists(image_path):
            try:
                image = Image.open(image_path)
                image = image.resize((250, 200), Image.Resampling.LANCZOS)
                
                # Convert image to base64 for API response
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                return f"data:image/png;base64,{img_str}"
            except Exception as e:
                print(f"Error loading image {image_path}: {e}")
                return None
    
    return None

# API Routes
@app.get("/")
async def root():
    return {"message": "FMECA Hardware Integrations API"}

@app.get("/boards", response_model=List[BoardInfo])
async def get_boards():
    boards = []
    for board_id, board_name in BOARD_NAMES.items():
        image_data = load_board_image(board_id)
        boards.append(BoardInfo(id=board_id, name=board_name, image=image_data))
    return boards

@app.post("/fmeca-data/{board_id}")
async def get_fmeca_data(board_id: int, filter_request: FilterRequest):
    try:
        df = load_main_data()
        ref_df = load_reference_data()
        
        selected_columns = ["ID", "Component", "Reference Designator", "RPN (S x O x D)"]
        base_df = df[selected_columns].iloc[3:]
        base_df["RPN (S x O x D)"] = pd.to_numeric(base_df["RPN (S x O x D)"], errors='coerce')

        # Apply filters
        if filter_request.filter_type == "red":
            df_filtered = base_df[base_df["RPN (S x O x D)"] >= 70]
        elif filter_request.filter_type == "orange":
            df_filtered = base_df[(base_df["RPN (S x O x D)"] < 70) & (base_df["RPN (S x O x D)"] >= 60)]
        elif filter_request.filter_type == "yellow":
            df_filtered = base_df[(base_df["RPN (S x O x D)"] < 60) & (base_df["RPN (S x O x D)"] >= 50)]
        elif filter_request.filter_type == "green":
            df_filtered = base_df[base_df["RPN (S x O x D)"] < 50]
        elif filter_request.filter_type == "all":
            df_filtered = base_df
        else:
            df_filtered = base_df

        # Sort and add ATM Coverage
        if filter_request.filter_type != "atm":
            df_filtered = df_filtered.sort_values(by="RPN (S x O x D)", ascending=False)
            df_filtered["Reference Designator"] = df_filtered["Reference Designator"].astype(str).str.upper()
            ref_df["CRD"] = ref_df["CRD"].astype(str).str.upper()

            df_filtered["ATM Coverage"] = "Not Found"

            for _, row in ref_df.iterrows():
                crd = str(row["CRD"]).strip()
                result_val = str(row["Result"])
                
                crd_designators = extract_complete_designators(crd)
                
                for designator in crd_designators:
                    mask = df_filtered["Reference Designator"].str.contains(re.escape(designator), na=False, regex=True)
                    df_filtered.loc[mask, "ATM Coverage"] = result_val

            # Convert to list of dictionaries for response
            result_data = []
            for _, row in df_filtered.iterrows():
                result_data.append({
                    "ID": str(row["ID"]),
                    "Component": str(row["Component"]),
                    "Reference_Designator": str(row["Reference Designator"]),
                    "RPN": str(row["RPN (S x O x D)"]),
                    "ATM_Coverage": str(row["ATM Coverage"])
                })
            
            return {"data": result_data, "count": len(result_data)}
        
        return {"data": [], "count": 0}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/atm-check/{board_id}", response_model=ATMResponse)
async def atm_check(board_id: int):
    try:
        df = load_main_data()
        ref_df = load_reference_data()
        
        selected_columns = ["ID", "Component", "Reference Designator", "RPN (S x O x D)"]
        base_df = df[selected_columns].iloc[3:]
        
        # Extract designators from FMECA
        fmeca_designators = set()
        for designator_str in base_df["Reference Designator"]:
            extracted = extract_designators(designator_str)
            fmeca_designators.update(extracted)
        
        # Extract designators from iiGD
        iigd_designators = set()
        for crd_str in ref_df["CRD"]:
            extracted = extract_complete_designators(crd_str)
            iigd_designators.update(extracted)
        
        # Find missing components
        truly_missing = set()
        for iigd_designator in iigd_designators:
            if not check_designator_in_fmeca(iigd_designator, fmeca_designators):
                truly_missing.add(iigd_designator)
        
        truly_missing = {d for d in truly_missing if d and len(d) > 1 and d not in ['NAN', 'NONE', 'NAT', 'NULL', 'NA']}
        
        # Create missing components list
        missing_components = []
        for missing_designator in sorted(truly_missing):
            result_value = find_result_for_designator(missing_designator, ref_df)
            missing_components.append(MissingComponent(
                component=missing_designator,
                atm_coverage=result_value
            ))
        
        if missing_components:
            message = f"ATM Check: {len(truly_missing)} values found in iiGD but missing in FMECA"
        else:
            message = "🎉 ATM Check: All CRD values from iiGD sheet are present in FMECA Reference Designator"
        
        return ATMResponse(
            missing_components=missing_components,
            message=message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)