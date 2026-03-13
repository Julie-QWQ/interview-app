# Prompt Templates

This directory stores Jinja2 prompt templates for the interview system.

Files:
- `interviewer_system_prompt.j2`: canonical structure for the interviewer system prompt.
- `VARIABLES.md`: context variables expected by the template.

Current status:
- The runtime prompt is now rendered from Jinja2 through a Python builder.
- The builder fills prompt context incrementally before rendering the final system prompt.
