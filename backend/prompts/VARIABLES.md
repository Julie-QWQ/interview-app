# Jinja2 Variables

`interviewer_system_prompt.j2` uses the following variables.

## Root Variables

- `base_system_prompt`: `str`, base identity/instruction text for the interviewer.
- `interviewer_style_prompt`: `str`, reusable interviewer speaking-style and conversation-behavior block.
- `tool_context_template`: `str`, Jinja2 template string used to render `tool_context_combined`.
- `position_profile`: `dict | None`, normalized position profile block.
- `interviewer_profile`: `dict | None`, normalized interviewer profile block.
- `interview`: `dict`, interview-level parameters.
- `stage`: `dict`, current stage metadata.
- `progress`: `dict | None`, interview progress data for follow-up turns.
- `tool_context`: `dict[str, str]`, raw tool prompt context blocks keyed by tool name.
- `tool_context_combined`: `str`, all tool outputs combined into one prompt block for the main interviewer prompt.
- `tool_summary`: `str`, short summary of tool usage for the current turn.
- `tool_constraints`: `list[str]`, constraints the interviewer should respect when using tool outputs.

## tool_context_template Variables

- `tool_context_items`: `list[dict]`, ordered tool context items used to render `tool_context_combined`.
- `tool_context`: `dict[str, str]`, raw tool prompt context blocks keyed by tool name.

Each `tool_context_items` entry contains:

- `tool_name`: `str`
- `context_label`: `str`
- `prompt_context`: `str`
- `structured_payload`: `dict`, tool-specific structured data. There is no global fixed field set.

## Tool Result Prompt Template Variables

Each tool's `result_prompt_template` can use:

- `tool_name`: `str`
- `structured_payload`: `dict`, defined by the current tool's own provider contract
- `raw_prompt_context`: `str`
- `summary`: `str`
- `meta`: `dict`

Notes:

- `structured_payload` is intentionally tool-specific. Do not assume every tool returns fields like `action_key`, `rationale`, or `utterance`.
- `smart_reply_engine` is a special case that does use `action_key / action_label / rationale / utterance`.
- If a tool does not return structured fields you need, prefer `{{ raw_prompt_context }}` in its `result_prompt_template`.

## position_profile

- `name`: `str`
- `description`: `str`
- `core_skills`: `list[str]`
- `ability_weights`: `dict[str, float | int | str]`

## interviewer_profile

- `name`: `str`
- `description`: `str`
- `prompt`: `str`
- `difficulty`: `str`
- `style_tone`: `str`

## interview

- `position`: `str`
- `skills`: `list[str]`
- `experience_level`: `str`
- `additional_requirements`: `str`

## stage

- `system_instruction`: `str`

## progress

- `stage_name`: `str`
- `current_turn`: `int`
- `turn_in_stage`: `int`
- `stage_max_turns`: `int`
- `overall_progress`: `int`
- `remaining_turns`: `int`

## tool_context

- `tool_context.resume_analyzer`: `str`, rendered prompt block for the resume analyzer.
- `tool_context.question_bank_retriever`: `str`, rendered prompt block for the question retriever.
- `tool_context.followup_engine`: `str`, rendered prompt block for follow-up suggestions.
- `tool_context.smart_reply_engine`: `str`, rendered prompt block for smart reply guidance.
