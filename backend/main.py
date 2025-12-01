from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import re
import os
from PIL import Image, ImageDraw
import io
import base64
from typing import List, Dict, Any, Optional

app = FastAPI(title="FMECA Hardware Integrations API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Board configuration with file paths
BOARD_CONFIG = {
    1: {"name": "IMD", "fmeca_file": "boards/IMD/fmeca.xlsx", "coverage_file": "boards/IMD/coverage.xlsx"},
    2: {"name": "SCR", "fmeca_file": "boards/SCR/fmeca.xlsx", "coverage_file": "boards/SCR/coverage.xlsx"},
    3: {"name": "PHTR", "fmeca_file": "boards/PHTR/fmeca.xlsx", "coverage_file": "boards/PHTR/coverage.xlsx"},
    4: {"name": "VSLD", "fmeca_file": "boards/VSLD/fmeca.xlsx", "coverage_file": "boards/VSLD/coverage.xlsx"},
    5: {"name": "CLBD", "fmeca_file": "boards/CLBD/fmeca.xlsx", "coverage_file": "boards/CLBD/coverage.xlsx"},
    6: {"name": "SVMC", "fmeca_file": "boards/SVMC/fmeca.xlsx", "coverage_file": "boards/SVMC/coverage.xlsx"},
    7: {"name": "IPSI", "fmeca_file": "boards/IPSI/fmeca.xlsx", "coverage_file": "boards/IPSI/coverage.xlsx"},
    8: {"name": "MPS", "fmeca_file": "boards/MPS/fmeca.xlsx", "coverage_file": "boards/MPS/coverage.xlsx"},
    9: {"name": "CC", "fmeca_file": "boards/CC/fmeca.xlsx", "coverage_file": "boards/CC/coverage.xlsx"}
}

# Pydantic models
class BoardInfo(BaseModel):
    id: int
    name: str
    image: Optional[str] = None

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

def create_colored_placeholder(board_name, board_id):
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

def load_board_image(board_id):
    board_config = BOARD_CONFIG.get(board_id)
    if not board_config:
        return None
        
    board_name = board_config["name"]
    
    image_paths = [
        f"boards/{board_name}/{board_name}.png",
        f"boards/{board_name}/image.png",
        f"boards/{board_name}.png",
        f"boards/Board {board_id}.png",
        f"boards/{board_name}.jpg",
        f"boards/{board_name}.jpeg",
    ]
    
    for image_path in image_paths:
        if os.path.exists(image_path):
            try:
                print(f"✅ Loading image: {image_path}")
                image = Image.open(image_path)
                image = image.resize((250, 200), Image.Resampling.LANCZOS)
                
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                return f"data:image/png;base64,{img_str}"
            except Exception as e:
                print(f"❌ Error loading {image_path}: {e}")
                continue
    
    print(f"⚠️ No image found for {board_name}, using placeholder")
    return create_colored_placeholder(board_name, board_id)

# ✅ UPDATED: Excel file loading functions
def load_main_data(board_id):
    """Load FMECA data for specific board"""
    try:
        board_config = BOARD_CONFIG.get(board_id)
        if not board_config:
            raise HTTPException(status_code=404, detail="Board not found")
        
        fmeca_file = board_config["fmeca_file"]
        print(f"📂 Loading FMECA file: {fmeca_file}")
        
        if not os.path.exists(fmeca_file):
            print(f"❌ FMECA file not found: {fmeca_file}")
            return pd.DataFrame()
        
        # Try different sheet names
        sheet_names = ['DFMECA', 'Sheet1', 'FMECA', 'Data']
        df = None
        
        for sheet in sheet_names:
            try:
                df = pd.read_excel(fmeca_file, sheet_name=sheet)
                print(f"✅ Loaded from sheet: {sheet}")
                break
            except:
                continue
        
        if df is None:
            # If no specific sheet found, try first sheet
            df = pd.read_excel(fmeca_file)
            print("✅ Loaded from first available sheet")
        
        df = df.ffill()
        print(f"✅ FMECA data loaded: {len(df)} rows")
        return df
    except Exception as e:
        print(f"❌ Error loading FMECA data: {e}")
        return pd.DataFrame()

def load_reference_data(board_id):
    """Load coverage data for specific board"""
    try:
        board_config = BOARD_CONFIG.get(board_id)
        if not board_config:
            raise HTTPException(status_code=404, detail="Board not found")
        
        coverage_file = board_config["coverage_file"]
        print(f"📂 Loading coverage file: {coverage_file}")
        
        if not os.path.exists(coverage_file):
            print(f"❌ Coverage file not found: {coverage_file}")
            return pd.DataFrame()
        
        # Try different sheet names
        sheet_names = ['iiGD board', 'Sheet1', 'Coverage', 'Data', 'ATM']
        ref_df = None
        
        for sheet in sheet_names:
            try:
                ref_df = pd.read_excel(coverage_file, sheet_name=sheet)
                print(f"✅ Loaded from sheet: {sheet}")
                break
            except:
                continue
        
        if ref_df is None:
            # If no specific sheet found, try first sheet
            ref_df = pd.read_excel(coverage_file)
            print("✅ Loaded from first available sheet")
        
        print(f"✅ Coverage data loaded: {len(ref_df)} rows")
        return ref_df
    except Exception as e:
        print(f"❌ Error loading coverage data: {e}")
        return pd.DataFrame()

# ✅ UPDATED: Utility functions for data processing
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

# API Routes
@app.get("/")
async def root():
    return {"message": "FMECA Hardware Integrations API"}

@app.get("/boards", response_model=List[BoardInfo])
async def get_boards():
    print("🎯 /boards API called")
    boards = []
    for board_id, board_config in BOARD_CONFIG.items():
        print(f"🔍 Processing board: {board_config['name']} (ID: {board_id})")
        
        image_data = load_board_image(board_id)
        boards.append(BoardInfo(
            id=board_id, 
            name=board_config["name"], 
            image=image_data
        ))
    
    print("✅ All boards processed successfully")
    return boards

# ✅ UPDATED: FMECA Data API with actual Excel processing
@app.post("/fmeca-data/{board_id}")
async def get_fmeca_data(board_id: int, filter_request: FilterRequest):
    try:
        print(f"📊 FMECA data requested for board {board_id} with filter {filter_request.filter_type}")
        
        df = load_main_data(board_id)
        ref_df = load_reference_data(board_id)
        
        if df.empty:
            return {"data": [], "count": 0, "message": "No FMECA data found"}
        
        if ref_df.empty:
            return {"data": [], "count": 0, "message": "No coverage data found"}
        
        # Find relevant columns
        id_col = None
        component_col = None
        designator_col = None
        rpn_col = None
        
        # Common column name patterns
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
        
        # If specific columns not found, use first few columns
        if not all([id_col, component_col, designator_col, rpn_col]):
            cols = df.columns.tolist()
            if len(cols) >= 4:
                id_col = cols[0] if not id_col else id_col
                component_col = cols[1] if not component_col else component_col
                designator_col = cols[2] if not designator_col else designator_col
                rpn_col = cols[3] if not rpn_col else rpn_col
        
        print(f"📝 Using columns - ID: {id_col}, Component: {component_col}, Designator: {designator_col}, RPN: {rpn_col}")
        
        # Create base dataframe
        selected_columns = [id_col, component_col, designator_col, rpn_col]
        base_df = df[selected_columns].copy()
        
        # Clean RPN column
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

        # Sort by RPN
        df_filtered = df_filtered.sort_values(by=rpn_col, ascending=False)
        
        # Add ATM Coverage
        df_filtered["ATM Coverage"] = "Not Found"
        
        # Find CRD and Result columns in reference data
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

        # Convert to response format
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

# ✅ UPDATED: ATM Check API
@app.get("/atm-check/{board_id}", response_model=ATMResponse)
async def atm_check(board_id: int):
    try:
        print(f"🏧 ATM check requested for board {board_id}")
        
        df = load_main_data(board_id)
        ref_df = load_reference_data(board_id)
        
        if df.empty or ref_df.empty:
            return ATMResponse(
                missing_components=[],
                message="Excel files not found or empty"
            )
        
        # Find designator column in FMECA data
        designator_col = None
        for col in df.columns:
            if 'reference' in str(col).lower() and 'designator' in str(col).lower():
                designator_col = col
                break
        
        if not designator_col:
            designator_col = df.columns[2] if len(df.columns) > 2 else df.columns[0]
        
        # Find CRD column in reference data
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
        
        # Extract designators
        fmeca_designators = set()
        for designator_str in df[designator_col]:
            extracted = extract_designators(designator_str)
            fmeca_designators.update(extracted)
        
        iigd_designators = set()
        for crd_str in ref_df[crd_col]:
            extracted = extract_complete_designators(crd_str)
            iigd_designators.update(extracted)
        
        # Find missing components
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
        
        # Create missing components list
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