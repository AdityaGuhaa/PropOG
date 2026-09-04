# PropOG AI Listing Cleaner

This is a small full-stack application that cleans raw property listing notes and extracts structured data (BHK, property type, locality, area) using the Google Gemini API. It enforces strict business rules and ensures the AI does not hallucinate data.

## Stack
Python
FastAPI
Pydantic
Gemini
HTML/CSS/JS

## Setup

Navigate to the backend directory and set up a virtual environment:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

For Windows:
```bash
.venv\Scripts\activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory and add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Run the backend server:
```bash
uvicorn main:app --reload
```

## API

### `POST /api/clean`
Accepts a raw property listing and returns structured data.

**Example Request:**
```json
{
  "description": "3bhk flat near metro good location 2200 sqft"
}
```

**Example Response:**
```json
{
  "headline": "3 BHK Flat Near Metro",
  "short_description": "A spacious 3 BHK flat located near the metro station, offering 2200 sqft of area.",
  "tags": ["3 BHK", "Flat", "Near Metro"],
  "bhk": 3,
  "property_type": "flat",
  "locality": "near metro",
  "area_sqft": 2200,
  "missing_fields": []
}
```

### `GET /health`
Returns the status of the API.
```json
{
  "status": "ok"
}
```

## Testing

You can use the frontend by simply opening `frontend/index.html` in your browser. Ensure the backend is running.

Test cases provided in the spec:
1. `3bhk flat near metro good location owner selling urgent need cash contact soon 2200 sqft parking available gym swimming pool`
2. `1bhk near office rent immediate no brokers`
3. `Spacious 4BHK villa in Sector 62, fully furnished, with clubhouse, power backup, and lift access. Ready to move, price slightly negotiable.`
