"""Interview stage progress utilities."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StageConfig:
    """Runtime stage config."""

    stage: str
    name: str
    description: str
    max_turns: int
    min_turns: int
    time_allocation: int
    system_instruction: str
    enabled: bool = True
    order: int = 0


def stage_config_from_model(stage_model) -> StageConfig:
    """Build runtime stage config from pydantic model."""
    return StageConfig(
        stage=stage_model.stage,
        name=stage_model.name,
        description=stage_model.description,
        max_turns=stage_model.max_turns,
        min_turns=stage_model.min_turns,
        time_allocation=stage_model.time_allocation,
        system_instruction=stage_model.system_instruction,
        enabled=stage_model.enabled,
        order=getattr(stage_model, "order", 0),
    )


class InterviewProgress:
    """Stage-aware interview progress manager."""

    def __init__(self, stages: List[StageConfig], total_duration_minutes: int = 30):
        self.total_duration_minutes = total_duration_minutes
        default_order_map = {
            "welcome": 1,
            "technical": 2,
            "scenario": 3,
            "closing": 4,
        }
        ordered = sorted(
            stages,
            key=lambda s: (
                s.order if s.order > 0 else default_order_map.get(s.stage, 999),
                s.stage,
            ),
        )
        self.stages = [s for s in ordered if s.enabled]
        if not self.stages:
            self.stages = ordered
        if not self.stages:
            self.stages = [
                StageConfig(
                    stage="default",
                    name="默认阶段",
                    description="系统默认阶段",
                    max_turns=10,
                    min_turns=1,
                    time_allocation=total_duration_minutes,
                    system_instruction="请继续面试并保持专业。",
                    enabled=True,
                    order=1,
                )
            ]

    def get_first_stage(self) -> str:
        return self.stages[0].stage

    def determine_stage(self, current_turn: int, elapsed_minutes: float = None) -> str:
        """Determine stage by current turn."""
        _ = elapsed_minutes
        if current_turn <= 0:
            return self.get_first_stage()

        turn_threshold = 0
        for stage in self.stages:
            turn_threshold += max(1, stage.max_turns)
            if current_turn <= turn_threshold:
                return stage.stage

        return self.stages[-1].stage

    def get_stage_info(self, stage_key: str) -> StageConfig:
        for stage in self.stages:
            if stage.stage == stage_key:
                return stage
        return self.stages[-1]

    def calculate_progress(self, current_turn: int, stage_key: str) -> Dict:
        """Calculate stage and overall progress info."""
        stage = self.get_stage_info(stage_key)

        turns_before_stage = 0
        for s in self.stages:
            if s.stage == stage.stage:
                break
            turns_before_stage += max(1, s.max_turns)

        stage_max_turns = max(1, stage.max_turns)
        turn_in_stage = max(0, current_turn - turns_before_stage)
        stage_progress = min(100, int((turn_in_stage / stage_max_turns) * 100))

        total_max_turns = sum(max(1, s.max_turns) for s in self.stages)
        overall_progress = min(100, int((current_turn / max(1, total_max_turns)) * 100))

        return {
            "current_stage": stage.stage,
            "stage_name": stage.name,
            "stage_description": stage.description,
            "turn_in_stage": turn_in_stage,
            "stage_max_turns": stage_max_turns,
            "stage_progress": stage_progress,
            "overall_turn": current_turn,
            "overall_progress": overall_progress,
            "remaining_turns": max(0, total_max_turns - current_turn),
        }
