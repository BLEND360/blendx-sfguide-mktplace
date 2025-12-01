from fastapi import APIRouter, HTTPException, status

from app.api.models.nl_ai_generator_models import (
    NLAIGeneratorRequest,
    NLAIGeneratorResponse,
)
from app.services.nl_ai_generator_service import generate_nl_ai_payload

router = APIRouter()


@router.post(
    "/nl-ai-generator",
    response_model=NLAIGeneratorResponse,
    status_code=status.HTTP_200_OK,
    tags=["NL AI Generator"],
)
async def nl_ai_generator_endpoint(request: NLAIGeneratorRequest):
    """
    Generate CrewAI YAML configuration from natural language.

    Uses pre-classification to determine Flow vs Crew, then generates
    with only the relevant template for better accuracy and efficiency.
    """
    result, error = generate_nl_ai_payload(request.user_request)

    if error:
        raise HTTPException(status_code=400, detail=error)
    return NLAIGeneratorResponse(**result)
