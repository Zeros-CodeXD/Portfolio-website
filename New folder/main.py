import os
from datetime import date
from fastapi import FastAPI, Query, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from scraper import sweep_domain 

app = FastAPI(
    title="Titan Intel Engine",
    description="Premium B2B Domain Contact Vector Scraper API",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. THE SECURITY KEYS
DEMO_API_KEY = "TitanIntelDemoPlaygroundSecretKey2026"
ADMIN_API_KEY = "TitanIntelMasterOverrideKey2026" # Your personal unlimited key

# 2. IN-MEMORY IP TRACKER
demo_usage_tracker = {}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "Titan Intel Engine v1.1.0"}

@app.get("/v1/sweep")
async def handle_sweep(
    request: Request,
    domain: str = Query(..., description="Target root domain to scan"),
    match_email_domain: bool = Query(False, description="Filter out external provider emails"),
    x_api_key: str = Header(None, alias="X-API-Key"),
    x_demo_key: str = Header(None, alias="X-Demo-Key"),
    x_rapidapi_plan: str = Header(None, alias="X-RapidAPI-Plan")
):
    is_rapidapi = "x-rapidapi-proxy-secret" in request.headers or "x-rapidapi-user" in request.headers
    is_demo_ui = (x_demo_key == DEMO_API_KEY or x_api_key == DEMO_API_KEY)
    is_admin = (x_demo_key == ADMIN_API_KEY or x_api_key == ADMIN_API_KEY)

    if not (is_rapidapi or is_demo_ui or is_admin):
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized access. Please use RapidAPI."
        )

    # 3. ENFORCE THE 5-REQUEST DAILY DEMO LIMIT (Unless it's you)
    if is_demo_ui and not is_admin:
        client_ip = request.client.host
        today = str(date.today())
        
        # Get user's current record or create a new one
        user_data = demo_usage_tracker.get(client_ip, {"date": today, "count": 0})
        
        # Reset if it's a new day
        if user_data["date"] != today:
            user_data = {"date": today, "count": 0}
            
        # Block if they hit 5 requests
        if user_data["count"] >= 5:
            raise HTTPException(
                status_code=429, 
                detail="DAILY LIMIT REACHED: You have used your 5 free demo searches. Subscribe on RapidAPI to unlock the commercial engine."
            )
            
        # Add 1 to their count and save it
        user_data["count"] += 1
        demo_usage_tracker[client_ip] = user_data

    has_ultra_access = is_admin or is_demo_ui or (x_rapidapi_plan and x_rapidapi_plan.lower() == "ultra")

    try:
        raw_data = await sweep_domain(domain, allow_deep_crawl=has_ultra_access)
        
        if match_email_domain and "emails" in raw_data:
            clean_domain = domain.lower().replace("www.", "")
            raw_data["emails"] = [
                email for email in raw_data["emails"] 
                if email.lower().endswith(f"@{clean_domain}")
            ]
            
        return {
            "status": "OK",
            "request_id": os.urandom(8).hex(),
            "data": raw_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping exception: {str(e)}")

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    return FileResponse("static/index.html")
