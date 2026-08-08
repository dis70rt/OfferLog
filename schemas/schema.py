from datetime import datetime, date, timezone
from typing import Optional
from pydantic import BaseModel, Field

class LLMOfferExtraction(BaseModel):
    """
    Schema passed to the LLM (via function calling or JSON mode) to extract job details from email text.
    The descriptive fields guide the AI to return high-quality data.
    """
    relevant: bool = Field(..., description="Whether the email relates to a job application or interview process.")
    company: Optional[str] = Field(None, description="The name of the company offering the job or sending the application update.")
    role: Optional[str] = Field(None, description="The job title or role the candidate applied for.")
    status: Optional[str] = Field(None, description="The current status of the application. Examples: 'Applied', 'Assessment', 'Assessment Complete', 'Interview', 'Rejected', 'Offer', 'On Hold', 'Unclear'.")
    next_step: Optional[str] = Field(None, description="A brief description of what the candidate needs to do next, if applicable (e.g., 'Schedule technical interview', 'Fill out background check').")
    next_step_date: Optional[date] = Field(None, description="The deadline or scheduled date for the next step, if mentioned in the email. Format as YYYY-MM-DD.")

class OfferRecord(LLMOfferExtraction):
    """
    Full schema for storing the merged job offer details, combining LLM extraction with Gmail metadata.
    """
    
    # Email Metadata (from Gmail API)
    date_received: Optional[date] = Field(None, description="The date the email was received.")
    email_subject: str = Field(..., description="The subject line of the email.")
    sender: str = Field(..., description="The sender of the email.")
    message_id: str = Field(..., description="The unique Gmail message ID.")
    thread_id: Optional[str] = Field(None, description="The Gmail thread ID for deduplication.")
    
    # System/Processing Metadata
    archived: bool = Field(False, description="Whether the record has been archived.")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the record was processed by the system.")
    raw_metadata_json: Optional[str] = Field(None, description="Raw JSON metadata string for debugging.")
