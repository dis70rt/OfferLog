from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class AuditRecord(BaseModel):
    """Schema for storing metadata and audit logs for OpenRouter API runs."""
    
    run_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: str
    status: str  # e.g., 'success', 'parse_error', 'api_error'
    
    generation_id: Optional[str] = None
    model: Optional[str] = None
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    @classmethod
    def from_openrouter_metadata(cls, message_id: str, status: str, metadata: dict = None):
        """
        Helper method to construct an AuditRecord from the raw OpenRouter metadata dict.
        """
        if not metadata:
            metadata = {}
            
        usage = metadata.get("usage", {})
        
        # Handle reasoning tokens which are nested
        completion_details = usage.get("completion_tokens_details", {})
        reasoning_tokens = completion_details.get("reasoning_tokens", 0)
        
        return cls(
            message_id=message_id,
            status=status,
            generation_id=metadata.get("id"),
            model=metadata.get("model"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            reasoning_tokens=reasoning_tokens,
            total_tokens=usage.get("total_tokens", 0),
            cost_usd=usage.get("cost", 0.0)
        )
