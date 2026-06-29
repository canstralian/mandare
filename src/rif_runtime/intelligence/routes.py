from fastapi import APIRouter

from .schemas import IntelligenceRequest, IntelligenceResponse
from .service import generate_intelligence

router = APIRouter(prefix="/v1/intelligence", tags=["intelligence"])


@router.post("/generate", response_model=IntelligenceResponse)
def generate(request: IntelligenceRequest) -> IntelligenceResponse:
    return generate_intelligence(request)
