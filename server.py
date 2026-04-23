from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import asyncio
import resend
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone

# TOP of file — yeh add karo
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase setup
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

supabase_client = None
supabase_available = False

try:
    if SUPABASE_URL and SUPABASE_KEY and 'demo-project' not in SUPABASE_URL:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase_available = True
except Exception as e:
    logging.warning(f"Supabase not available: {e}. Contact form will still send emails.")

# Resend API setup
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', 'ejazhamza28@gmail.com')

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class ContactFormRequest(BaseModel):
    name: str
    email: EmailStr
    whatsapp: str
    company: Optional[str] = None
    message: str

class ContactSubmission(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    whatsapp: str
    company: Optional[str] = None
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# In-memory fallback when Supabase is not configured
status_checks_store = []
contact_submissions_store = []

@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.model_dump())
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()

    if supabase_available:
        try:
            supabase_client.table("status_checks").insert(doc).execute()
        except Exception as e:
            logger.warning(f"Supabase insert failed: {e}")
            status_checks_store.append(doc)
    else:
        status_checks_store.append(doc)

    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    if supabase_available:
        try:
            result = supabase_client.table("status_checks").select("*").execute()
            checks = result.data or []
            for c in checks:
                if isinstance(c.get('timestamp'), str):
                    c['timestamp'] = datetime.fromisoformat(c['timestamp'])
            return checks
        except Exception as e:
            logger.warning(f"Supabase query failed: {e}")

    for c in status_checks_store:
        if isinstance(c.get('timestamp'), str):
            c['timestamp'] = datetime.fromisoformat(c['timestamp'])
    return status_checks_store

@api_router.post("/contact")
async def submit_contact_form(request: ContactFormRequest):
    logger.info(f"Contact form received from {request.email}")
    
    try:
        submission = ContactSubmission(
            name=request.name,
            email=request.email,
            whatsapp=request.whatsapp,
            company=request.company,
            message=request.message
        )

        doc = submission.model_dump()
        doc["timestamp"] = submission.timestamp.isoformat()

        # Store in Supabase
        db_success = False
        
        if supabase_available:
            try:
                logger.info(f"Attempting Supabase insert for {request.email}")
                result = supabase_client.table("contact_submissions").insert(doc).execute()
                logger.info(f"Supabase insert result: {result}")
                db_success = True
            except Exception as db_err:
                logger.error(f"Supabase insert FAILED: {db_err}")
                contact_submissions_store.append(doc)
        else:
            logger.warning("Supabase not available, using in-memory store")
            contact_submissions_store.append(doc)

        # Send email via Resend
        logger.info(f"Attempting to send email for {request.email}")
        logger.info(f"Resend API Key set: {bool(resend.api_key)}")
        logger.info(f"Sender: {SENDER_EMAIL}, Recipient: {RECIPIENT_EMAIL}")

        # Send email via Resend
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #00A3A8; border-bottom: 2px solid #00A3A8; padding-bottom: 10px;">
                New Contact Form Submission - OZlume
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr>
                    <td style="padding: 10px; background: #f5f5f5; font-weight: bold; width: 30%;">Name:</td>
                    <td style="padding: 10px; background: #fff;">{request.name}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f5f5f5; font-weight: bold;">Email:</td>
                    <td style="padding: 10px; background: #fff;">{request.email}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f5f5f5; font-weight: bold;">WhatsApp:</td>
                    <td style="padding: 10px; background: #fff;">{request.whatsapp}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f5f5f5; font-weight: bold;">Company:</td>
                    <td style="padding: 10px; background: #fff;">{request.company or 'Not provided'}</td>
                </tr>
            </table>
            <div style="margin-top: 20px; padding: 15px; background: #f9f9f9; border-left: 4px solid #00A3A8;">
                <h3 style="margin: 0 0 10px 0; color: #333;">Message:</h3>
                <p style="margin: 0; color: #555; line-height: 1.6;">{request.message}</p>
            </div>
            <p style="margin-top: 30px; color: #888; font-size: 12px;">
                This email was sent from the OZlume website contact form.
            </p>
        </div>
        """

        params = {
            "from": SENDER_EMAIL,
            "to": [RECIPIENT_EMAIL],
            "subject": f"New Contact Form Submission from {request.name}",
            "html": html_content
        }

        try:
            email_response = await asyncio.to_thread(resend.Emails.send, params)
            logger.info(f"Email sent successfully: {email_response}")
        except Exception as email_error:
            logger.error(f"Email sending FAILED: {str(email_error)}")

        return {
            "status": "success",
            "message": "Thank you for your message! We'll get back to you within 24 hours."
        }

    except Exception as e:
        logger.error(f"Contact form submission FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit contact form. Please try again.")

@api_router.get("/submissions")
async def get_contact_submissions():
    if supabase_available:
        try:
            result = supabase_client.table("contact_submissions").select("*").order("timestamp", desc=True).execute()
            return {"submissions": result.data or []}
        except Exception as e:
            logger.warning(f"Supabase query failed: {e}")
    return {"submissions": contact_submissions_store}

app.include_router(api_router)

cors_origins = os.environ.get("CORS_ORIGINS", "*")

origins = cors_origins.split(",") if cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
