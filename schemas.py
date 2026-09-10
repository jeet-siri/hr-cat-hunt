from pydantic import BaseModel
from typing import Optional

class ScanRequest(BaseModel):
    employeeId: str
    name: str
    department: str
    cat: str
    token: str
    userAgent: Optional[str] = None
