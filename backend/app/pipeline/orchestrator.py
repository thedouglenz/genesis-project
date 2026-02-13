import uuid

from app.pipeline.answer import AnswerStep
from app.pipeline.base import PipelineStep
from app.pipeline.explore import ExploreStep
from app.pipeline.plan import PlanStep
from app.schemas.api import AnswerOutput


class Pipeline:
    """Orchestrates the multi-step pipeline: plan → explore → answer.

    For each step:
    - Load input from prior step output or initial context
    - Execute step with retry logic
    - Persist step input/output to pipeline_steps table
    - Stream progress via SSE
    - If step fails after max retries, persist error and abort
    """

    def __init__(self, conversation_id: uuid.UUID, message_id: uuid.UUID):
        self.conversation_id = conversation_id
        self.message_id = message_id
        self.steps: list[PipelineStep] = [PlanStep(), ExploreStep(), AnswerStep()]

    async def run(self, user_question: str) -> AnswerOutput:
        """Run the full pipeline and return the final answer."""
        raise NotImplementedError
