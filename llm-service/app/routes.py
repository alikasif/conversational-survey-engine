"""HTTP route handlers for the LLM service."""

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from .agents.generator_agent import generate_question, generate_preset_question_set
from .agents.answer_guardrails import check_answer
from .agents.validator import QuestionValidator
from .schemas import (
    CheckGuardrailsRequest,
    CheckGuardrailsResponse,
    GeneratePresetRequest,
    GeneratePresetResponse,
    GenerateQuestionRequest,
    GenerateQuestionResponse,
    PresetQuestion,
    ValidateQuestionRequest,
    ValidateQuestionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
validator = QuestionValidator()


@router.post("/generate-question", response_model=GenerateQuestionResponse)
async def handle_generate_question(req: GenerateQuestionRequest):
    """Generate a single survey question."""
    try:
        question_text = await generate_question(
            survey_context=req.survey_context,
            goal=req.goal,
            constraints=req.constraints,
            conversation_history=req.history_tuples,
            question_number=req.question_number,
            max_questions=req.max_questions,
            goal_coverage_threshold=req.goal_coverage_threshold,
            rejection_guardrail_hint=req.rejection_guardrail_hint,
        )
        return GenerateQuestionResponse(
            question_text=question_text,
            question_id=str(uuid4()),
        )
    except Exception as e:
        logger.error(f"Error generating question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate question")


@router.post("/validate-question", response_model=ValidateQuestionResponse)
async def handle_validate_question(req: ValidateQuestionRequest):
    """Validate a candidate survey question."""
    try:
        is_valid, reason = await validator.validate(
            candidate_question=req.question,
            goal=req.goal,
            context=req.survey_context,
            conversation_history=req.history_tuples,
        )
        issues = [reason] if reason else []
        return ValidateQuestionResponse(is_valid=is_valid, issues=issues)
    except Exception as e:
        logger.error(f"Error validating question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate question")


@router.post("/check-guardrails", response_model=CheckGuardrailsResponse)
async def handle_check_guardrails(req: CheckGuardrailsRequest):
    """Check answer guardrails (gibberish, injection)."""
    try:
        result = check_answer(req.answer)
        return CheckGuardrailsResponse(
            is_valid=not result.is_flagged,
            flags=result.flags,
            rejection_reason=result.rejection_hint,
        )
    except Exception as e:
        logger.error(f"Error checking guardrails: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check guardrails")


@router.post("/generate-preset-questions", response_model=GeneratePresetResponse)
async def handle_generate_preset_questions(req: GeneratePresetRequest):
    """Generate a full set of preset questions for a survey."""
    try:
        raw_questions = await generate_preset_question_set(
            survey_context=req.survey_context,
            goal=req.goal,
            constraints=req.constraints,
            count=req.count,
        )
        questions = [
            PresetQuestion(
                question_number=q["question_number"],
                question_id=q["question_id"],
                text=q["text"],
            )
            for q in raw_questions
        ]
        return GeneratePresetResponse(questions=questions)
    except Exception as e:
        logger.error(f"Error generating preset questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate preset questions")
