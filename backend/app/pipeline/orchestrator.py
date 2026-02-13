import uuid
from datetime import datetime

from sqlalchemy import select

from app.database import AppSession
from app.services import events
from app.models.app import Conversation, PipelineRun
from app.models.app import PipelineStep as PipelineStepModel
from app.pipeline.answer import AnswerStep
from app.pipeline.base import PipelineStep
from app.pipeline.explore import ExploreStep
from app.pipeline.plan import PlanStep
from app.schemas.api import AnswerOutput
from app.services.llm import LLMClient
from app.tools import ListTablesTool, QueryTool, SampleDataTool, ShowSchemaTool


class Pipeline:
    """Orchestrates the multi-step pipeline: plan → explore → answer.

    For each step:
    - Load input from prior step output or initial context
    - Execute step with retry logic
    - Persist step input/output to pipeline_steps table
    - If step fails after max retries, persist error and abort
    """

    def __init__(self, conversation_id: uuid.UUID, message_id: uuid.UUID):
        self.conversation_id = conversation_id
        self.message_id = message_id
        self.steps: list[PipelineStep] = [PlanStep(), ExploreStep(), AnswerStep()]

    async def run(
        self,
        user_question: str,
        conversation_history: list[dict] | None = None,
        schema_context: dict | None = None,
    ) -> AnswerOutput:
        """Run the full pipeline and return the final answer."""
        history = conversation_history or []
        llm_client = LLMClient()
        available_tools = [
            ListTablesTool(),
            ShowSchemaTool(),
            SampleDataTool(),
            QueryTool(),
        ]

        async with AppSession() as session:
            # Create pipeline run
            pipeline_run = PipelineRun(
                message_id=self.message_id,
                status="running",
            )
            session.add(pipeline_run)
            await session.commit()
            await session.refresh(pipeline_run)

            plan_output = None
            explore_output = None
            answer_output: AnswerOutput | None = None

            try:
                # Determine which steps to run
                active_steps: list[PipelineStep] = list(self.steps)  # [plan, explore, answer]

                for step_order, step in enumerate(active_steps):
                    # After plan, check if we should skip explore
                    if step.name == "explore" and plan_output and plan_output.skip_explore:
                        continue

                    # Build input data for each step
                    if step.name == "plan":
                        input_data = {
                            "question": user_question,
                            "history": history,
                            "schema_context": schema_context,
                        }
                    elif step.name == "explore":
                        input_data = {
                            "plan": plan_output.model_dump(),
                            "available_tools": available_tools,
                        }
                    elif step.name == "answer":
                        input_data = {
                            "question": user_question,
                            "plan": plan_output.model_dump(),
                            "exploration": explore_output.model_dump() if explore_output else None,
                            "history": history,
                        }
                    else:
                        raise ValueError(f"Unknown step: {step.name}")

                    # Create step record
                    serializable_input = {
                        k: v
                        for k, v in input_data.items()
                        if k != "available_tools"
                    }
                    step_record = PipelineStepModel(
                        pipeline_run_id=pipeline_run.id,
                        step_name=step.name,
                        step_order=step_order,
                        input_json=serializable_input,
                        status="running",
                        attempts=1,
                    )
                    session.add(step_record)
                    await session.commit()
                    await session.refresh(step_record)

                    # Emit running event
                    conv_id = str(self.conversation_id)
                    await events.emit(conv_id, {"step": step.name, "status": "running"})

                    # Execute step
                    result = await step.execute_with_retry(input_data, llm_client)

                    # Persist result
                    step_record.output_json = result.model_dump()
                    step_record.status = "completed"
                    step_record.completed_at = datetime.utcnow()
                    await session.commit()

                    # Emit completed event
                    completed_event: dict = {"step": step.name, "status": "completed"}
                    if step.name == "plan" and hasattr(result, "reasoning"):
                        completed_event["summary"] = result.reasoning[:100]
                    await events.emit(conv_id, completed_event)

                    # Track outputs for downstream steps
                    if step.name == "plan":
                        plan_output = result
                        # Update conversation title if the plan step produced a name
                        if plan_output.conversation_name:
                            convo_result = await session.execute(
                                select(Conversation).where(
                                    Conversation.id == self.conversation_id
                                )
                            )
                            convo = convo_result.scalar_one_or_none()
                            if convo and not convo.title:
                                convo.title = plan_output.conversation_name
                                await session.commit()
                    elif step.name == "explore":
                        explore_output = result
                    elif step.name == "answer":
                        answer_output = result

                # Mark pipeline run completed
                pipeline_run.status = "completed"
                pipeline_run.completed_at = datetime.utcnow()
                await session.commit()

                # Note: "done" event is emitted by _run_pipeline after message content is persisted

            except Exception as exc:
                pipeline_run.status = "failed"
                await session.commit()

                # Update last step with error
                db_result = await session.execute(
                    select(PipelineStepModel)
                    .where(PipelineStepModel.pipeline_run_id == pipeline_run.id)
                    .where(PipelineStepModel.status == "running")
                )
                failed_step = db_result.scalar_one_or_none()
                if failed_step:
                    failed_step.status = "failed"
                    failed_step.error = str(exc)
                    await session.commit()
                raise

            return answer_output  # type: ignore[return-value]
