import os
import json
from typing import List, Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env from the backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

# Initialize FastAPI app
app = FastAPI(title="PropOG AI Listing Cleaner")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev (including null from file://)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------

class ListingRequest(BaseModel):
    description: str

class ListingResponse(BaseModel):
    headline: str
    short_description: str
    tags: List[str]
    bhk: Optional[int] = None
    property_type: Optional[Literal["flat", "villa", "plot", "other"]] = None
    locality: Optional[str] = None
    area_sqft: Optional[float] = None
    missing_fields: List[str]

FIELDS = ["bhk", "property_type", "locality", "area_sqft"]
ALLOWED_PROPERTY_TYPES = ["flat", "villa", "plot", "other", None]

# -----------------------------------------------------------------------------
# AI and Business Logic
# -----------------------------------------------------------------------------

PROMPT = """You clean raw property listing notes.

Your task is to produce:
1. A concise property headline.
2. A short polished description.
3. 3 to 5 relevant tags.
4. Structured property information.

CRITICAL RULE:
NEVER INVENT INFORMATION.

Only return a structured value if the value is explicitly mentioned
in the raw listing.

If the input does not explicitly mention a field, return null.

Do not estimate.
Do not guess.
Do not infer.
Do not use common real-estate assumptions.

For example:
- "1bhk" does NOT prove that property_type is "flat".
- Missing area means area_sqft must be null.
- Missing locality means locality must be null.

Allowed property_type values:
flat
villa
plot
other
null

The final result must conform to the provided response schema.

RAW LISTING:
{listing_text}
"""

def call_gemini(description: str) -> dict:
    """Calls the Gemini API and returns the parsed JSON dict."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise HTTPException(status_code=500, detail="Gemini API key is not configured.")

    client = genai.Client(api_key=api_key)
    
    # We use a standard model suitable for fast text tasks.
    model_name = "gemini-3.5-flash" 
    
    prompt = PROMPT.format(listing_text=description)
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ListingResponse,
                temperature=0.0 # Low temperature for deterministic extraction
            )
        )
        # Parse the JSON response
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        raise ValueError("Failed to get a valid response from Gemini.")

def validate_business_rules(result: dict):
    """Validates the business rules that schema validation alone might miss."""
    
    # 1. Tags count
    tags = result.get("tags", [])
    if not isinstance(tags, list) or len(tags) < 3 or len(tags) > 5:
        raise ValueError("Tags must be between 3 and 5 items.")
        
    # 2. Property type allowed values
    prop_type = result.get("property_type")
    if prop_type not in ALLOWED_PROPERTY_TYPES:
        raise ValueError(f"Invalid property_type: {prop_type}")

def calculate_missing_fields(result: dict) -> List[str]:
    """Deterministically calculates missing fields."""
    return [field for field in FIELDS if result.get(field) is None]

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/clean", response_model=ListingResponse)
def clean_listing(request: ListingRequest):
    if not request.description or not request.description.strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty or whitespace.")

    # Implement a simple retry loop (max 1 retry -> total 2 attempts)
    max_attempts = 2
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            # 1. AI Call
            ai_result_dict = call_gemini(request.description)
            
            # 2. Parse via Pydantic (implicitly tests the schema matching)
            parsed_result = ListingResponse(**ai_result_dict)
            
            # 3. Validate business rules on the raw dict
            validate_business_rules(ai_result_dict)
            
            # 4. Calculate missing_fields deterministically
            ai_result_dict["missing_fields"] = calculate_missing_fields(ai_result_dict)
            
            # Ensure pydantic serializes the updated missing fields
            final_response = ListingResponse(**ai_result_dict)
            return final_response
            
        except (ValueError, TypeError) as e:
            last_error = str(e)
            print(f"Attempt {attempt + 1} failed validation: {last_error}")
            continue # Try again if we have attempts left
            
    # If we exhaust retries
    raise HTTPException(status_code=500, detail=f"Failed to process listing. Validation error: {last_error}")
