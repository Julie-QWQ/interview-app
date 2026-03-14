"""Resume Analyzer Tool Adapter for interview service integration.

This module provides integration with the external growth service (growth-service)
for resume parsing, skill extraction, and personalized question generation.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from app.services.interview_orchestrator import (
    ExternalToolAdapter,
    ToolExecutionContext,
    ToolResult,
)

logger = logging.getLogger(__name__)


class ResumeAnalyzerAdapter(ExternalToolAdapter):
    """Adapter for resume analyzer service integration.

    Supports:
    - Resume parsing and skill extraction
    - Personalized question generation based on resume
    - Candidate capability assessment
    - Project experience analysis
    """

    tool_name = "resume_analyzer"
    supported_stages = {
        "welcome",  # Initial resume analysis at interview start
        "technical_questions",  # Deep dive into technical skills
        "project_discussion",  # Project-based questions
        "behavioral_questions",  # Experience-based questions
    }
    supported_triggers = {
        "interview_start",  # Analyze resume when interview begins
        "stage_enter",  # Re-analyze for specific stages
        "user_message",  # Follow-up based on candidate responses
    }
    default_ttl_seconds = 1800  # Cache resume analysis for 30 minutes

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self._service_base_url: str = ""
        self._timeout: float = 5.0

    def _get_service_base_url(self) -> str:
        """Get the base URL for growth service."""
        if not self._service_base_url:
            cfg = self._provider_config()
            url = cfg.get("url", "http://localhost:8003/api/growth").rstrip("/")
            self._service_base_url = url
        return self._service_base_url

    def _get_timeout(self) -> float:
        """Get request timeout in seconds."""
        cfg = self._provider_config()
        return float(cfg.get("timeout_seconds", 5.0))

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests."""
        cfg = self._provider_config()
        headers = {"Content-Type": "application/json"}
        # Add custom headers from config
        custom_headers = cfg.get("headers") or {}
        headers.update(custom_headers)
        return headers

    def build_context_key(self, context: ToolExecutionContext) -> str:
        """Build cache key for tool context.

        Key structure: resume:{userId}:{interview_id}:{stage}
        """
        interview = context.interview_config or {}
        user_id = interview.get("user_id") or interview.get("candidate_id", "unknown")

        # Cache resume analysis per interview for efficiency
        # Different stages may use different aspects of the same resume
        if context.trigger == "interview_start":
            return f"resume:{user_id}:{context.interview_id}:initial"
        else:
            return f"resume:{user_id}:{context.interview_id}:{context.stage}"

    def build_params(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Build request parameters based on trigger type."""
        params = {}
        interview = context.interview_config or {}

        # Common parameters
        user_id = interview.get("user_id") or interview.get("candidate_id")
        if user_id:
            params["userId"] = user_id

        # Position and skill domain
        position = interview.get("position")
        if position:
            params["position"] = position

        skill_domain = interview.get("skill_domain")
        if skill_domain:
            params["skillDomain"] = skill_domain

        # Skills of interest
        skills = interview.get("skills") or []
        if skills:
            if isinstance(skills, list):
                params["skills"] = ",".join(str(s) for s in skills)
            else:
                params["skills"] = str(skills)

        return params

    def build_request(self, context: ToolExecutionContext) -> Dict[str, Any]:
        """Build request payload for growth service.

        Different triggers generate different API calls:
        - interview_start: Get and analyze full resume
        - stage_enter: Get specific resume aspects (skills/projects)
        - user_message: Deep dive into specific topics
        """
        trigger = context.trigger
        base_url = self._get_service_base_url()

        if trigger == "interview_start":
            return self._build_resume_analysis_request(context, base_url)
        elif trigger == "stage_enter":
            return self._build_stage_specific_request(context, base_url)
        elif trigger == "user_message":
            return self._build_followup_request(context, base_url)
        else:
            # Default: full resume analysis
            return self._build_resume_analysis_request(context, base_url)

    def _build_resume_analysis_request(self, context: ToolExecutionContext, base_url: str) -> Dict[str, Any]:
        """Build full resume analysis request."""
        interview = context.interview_config or {}
        user_id = interview.get("user_id") or interview.get("candidate_id")

        if not user_id:
            return {
                "method": "GET",
                "url": "",
                "error": "Missing user_id for resume analysis",
            }

        # First, try to get resume list for the user
        return {
            "method": "GET",
            "url": urljoin(base_url, "/resume/list"),
            "params": {"userId": user_id},
            "follow_up": "get_resume_detail",  # Flag to get detail after list
        }

    def _build_stage_specific_request(self, context: ToolExecutionContext, base_url: str) -> Dict[str, Any]:
        """Build stage-specific resume request."""
        interview = context.interview_config or {}
        user_id = interview.get("user_id") or interview.get("candidate_id")

        if not user_id:
            return {
                "method": "GET",
                "url": "",
                "error": "Missing user_id for resume analysis",
            }

        # For different stages, we might focus on different aspects
        # But first we need to get the resume
        return {
            "method": "GET",
            "url": urljoin(base_url, "/resume/list"),
            "params": {"userId": user_id},
            "stage": context.stage,
        }

    def _build_followup_request(self, context: ToolExecutionContext, base_url: str) -> Dict[str, Any]:
        """Build follow-up request based on user message."""
        # For follow-up, we analyze the user's response against resume claims
        # This can help detect inconsistencies or dive deeper into claims

        interview = context.interview_config or {}
        user_id = interview.get("user_id") or interview.get("candidate_id")

        if not user_id:
            return {
                "method": "GET",
                "url": "",
                "error": "Missing user_id for follow-up analysis",
            }

        # Get resume for cross-referencing
        return {
            "method": "GET",
            "url": urljoin(base_url, "/resume/list"),
            "params": {"userId": user_id},
            "user_message": context.current_user_message,
        }

    def call(self, payload: Dict[str, Any], *, timeout_seconds: float) -> ToolResult:
        """Execute the API call to growth service."""
        method = payload.get("method", "GET")
        url = payload.get("url", "")
        params = payload.get("params", {})

        if not url or payload.get("error"):
            return ToolResult(
                status="error",
                errors=[payload.get("error", "Invalid request")],
            )

        headers = self._build_headers()

        try:
            start_time = time.perf_counter()

            # Step 1: Get resume list
            if method == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout_seconds,
                )
            else:
                response = requests.post(
                    url,
                    json=params,
                    headers=headers,
                    timeout=timeout_seconds,
                )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response.raise_for_status()
            body = response.json()

            # Step 2: If we got a list, get the first resume's detail
            if payload.get("follow_up") == "get_resume_detail":
                resumes = body.get("data", [])
                if isinstance(resumes, list) and resumes:
                    first_resume = resumes[0]
                    resume_id = first_resume.get("id")

                    if resume_id:
                        return self._get_resume_detail(base_url=self._get_service_base_url(), resume_id=resume_id, initial_latency=latency_ms)
                    else:
                        return self._parse_resume_list(body, latency_ms)
                else:
                    return ToolResult(
                        status="success",
                        summary="No resumes found for user",
                        structured_payload={"resumes": []},
                        meta={"latency_ms": latency_ms},
                    )
            else:
                return self._parse_response(body, latency_ms)

        except requests.exceptions.Timeout:
            logger.error(f"Resume analyzer service timeout: {url}")
            return ToolResult(
                status="timeout",
                errors=["Resume analyzer service timeout"],
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Resume analyzer service error: {e}")
            return ToolResult(
                status="error",
                errors=[str(e)],
            )
        except Exception as e:
            logger.error(f"Unexpected error calling resume analyzer: {e}")
            return ToolResult(
                status="error",
                errors=[str(e)],
            )

    def _get_resume_detail(self, base_url: str, resume_id: int, initial_latency: int) -> ToolResult:
        """Get detailed resume information including parsed results."""
        try:
            url = urljoin(base_url, f"/resume/{resume_id}")
            headers = self._build_headers()

            start_time = time.perf_counter()
            response = requests.get(url, headers=headers, timeout=5.0)
            detail_latency_ms = int((time.perf_counter() - start_time) * 1000)

            total_latency_ms = initial_latency + detail_latency_ms
            response.raise_for_status()
            body = response.json()

            return self._parse_resume_detail(body, total_latency_ms)

        except Exception as e:
            logger.error(f"Error getting resume detail: {e}")
            return ToolResult(
                status="partial",
                summary=f"Resume list retrieved, but detail failed: {str(e)}",
                structured_payload={"resume_id": resume_id},
                meta={"latency_ms": initial_latency},
                errors=[str(e)],
            )

    def _parse_response(self, body: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse growth service response into ToolResult."""
        code = body.get("code", 500)
        message = body.get("message", "")
        data = body.get("data")

        if code != 200:
            return ToolResult(
                status="error",
                errors=[f"Resume analyzer error {code}: {message}"],
                raw_response=body,
            )

        # Handle resume list
        if isinstance(data, list):
            return self._parse_resume_list(body, latency_ms)

        # Handle single resume object
        if isinstance(data, dict):
            return self._parse_resume_detail(body, latency_ms)

        # Generic success response
        return ToolResult(
            status="success",
            summary=message or "Request completed",
            structured_payload={"data": data},
            raw_response=body,
        )

    def _parse_resume_list(self, body: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse resume list response."""
        resumes = body.get("data", [])

        if not resumes:
            return ToolResult(
                status="success",
                summary="No resumes found for user",
                structured_payload={"resumes": []},
                meta={"latency_ms": latency_ms},
            )

        # Build summary
        summary = f"Found {len(resumes)} resume(s):\n"
        for i, resume in enumerate(resumes[:3], 1):
            summary += f"{i}. {resume.get('fileName', 'Unknown')} "
            summary += f"({resume.get('parseStatus', 'Unknown')})\n"

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={
                "resumes": resumes,
                "count": len(resumes),
            },
            meta={"latency_ms": latency_ms, "resume_count": len(resumes)},
        )

    def _parse_resume_detail(self, body: Dict[str, Any], latency_ms: int) -> ToolResult:
        """Parse detailed resume response."""
        data = body.get("data", {})

        if not data:
            return ToolResult(
                status="error",
                errors=["Empty resume data"],
                raw_response=body,
            )

        # Extract key information
        file_name = data.get("fileName", "Unknown")
        parse_status = data.get("parseStatus", "UNKNOWN")
        parsed_json = data.get("parsedJson", {})
        raw_text = data.get("rawText", "")

        # Build summary
        summary = f"Resume: {file_name}\n"
        summary += f"Parse Status: {parse_status}\n"

        if parsed_json:
            # Extract skills
            skills = parsed_json.get("skills", [])
            if skills:
                summary += f"\nSkills ({len(skills)}): "
                if isinstance(skills, list):
                    summary += ", ".join(str(s) for s in skills[:10])
                else:
                    summary += str(skills)
                summary += "\n"

            # Extract projects
            projects = parsed_json.get("projects", [])
            if projects:
                summary += f"\nProjects ({len(projects)}):\n"
                for i, project in enumerate(projects[:3], 1):
                    if isinstance(project, dict):
                        name = project.get("name", "Unnamed")
                        role = project.get("role", "Unknown role")
                        summary += f"{i}. {name} ({role})\n"

            # Extract education
            education = parsed_json.get("education", [])
            if education:
                summary += f"\nEducation ({len(education)}):\n"
                for i, edu in enumerate(education[:2], 1):
                    if isinstance(edu, dict):
                        school = edu.get("school", "Unknown")
                        degree = edu.get("degree", "")
                        major = edu.get("major", "")
                        summary += f"{i}. {school} - {degree} {major}\n"

        # Build prompt context for AI
        prompt_context = self._build_resume_prompt_context(data)

        return ToolResult(
            status="success",
            summary=summary,
            structured_payload={
                "resume": data,
                "fileName": file_name,
                "parseStatus": parse_status,
                "parsedJson": parsed_json,
            },
            prompt_context=prompt_context,
            meta={
                "latency_ms": latency_ms,
                "file_name": file_name,
                "parse_status": parse_status,
                "has_parsed_data": bool(parsed_json),
            },
        )

    def _build_resume_prompt_context(self, resume_data: Dict[str, Any]) -> str:
        """Build prompt context from resume for AI."""
        context_parts = ["## Candidate Resume Analysis\n"]

        file_name = resume_data.get("fileName", "")
        if file_name:
            context_parts.append(f"**Resume File**: {file_name}\n")

        parsed_json = resume_data.get("parsedJson", {})

        if parsed_json:
            # Skills section
            skills = parsed_json.get("skills", [])
            if skills:
                context_parts.append("\n**Technical Skills**:\n")
                if isinstance(skills, list):
                    for skill in skills[:20]:  # Limit to top 20 skills
                        context_parts.append(f"- {skill}\n")
                else:
                    context_parts.append(f"{skills}\n")

            # Projects section
            projects = parsed_json.get("projects", [])
            if projects:
                context_parts.append("\n**Project Experience**:\n")
                for i, project in enumerate(projects[:5], 1):  # Limit to top 5 projects
                    if isinstance(project, dict):
                        name = project.get("name", "Unnamed Project")
                        role = project.get("role", "")
                        description = project.get("description", "")
                        technologies = project.get("technologies", [])

                        context_parts.append(f"{i}. **{name}**")
                        if role:
                            context_parts.append(f" ({role})")
                        context_parts.append("\n")

                        if description:
                            # Truncate long descriptions
                            desc = str(description)[:300]
                            if len(str(description)) > 300:
                                desc += "..."
                            context_parts.append(f"   - Description: {desc}\n")

                        if technologies:
                            if isinstance(technologies, list):
                                tech_str = ", ".join(str(t) for t in technologies)
                            else:
                                tech_str = str(technologies)
                            context_parts.append(f"   - Technologies: {tech_str}\n")

            # Work experience section
            work_experience = parsed_json.get("workExperience", [])
            if work_experience:
                context_parts.append("\n**Work Experience**:\n")
                for i, exp in enumerate(work_experience[:3], 1):
                    if isinstance(exp, dict):
                        company = exp.get("company", "Unknown Company")
                        position = exp.get("position", "")
                        duration = exp.get("duration", "")

                        context_parts.append(f"{i}. {company}")
                        if position:
                            context_parts.append(f" - {position}")
                        if duration:
                            context_parts.append(f" ({duration})")
                        context_parts.append("\n")

            # Education section
            education = parsed_json.get("education", [])
            if education:
                context_parts.append("\n**Education**:\n")
                for i, edu in enumerate(education[:2], 1):
                    if isinstance(edu, dict):
                        school = edu.get("school", "Unknown School")
                        degree = edu.get("degree", "")
                        major = edu.get("major", "")

                        context_parts.append(f"{i}. {school}")
                        if degree or major:
                            context_parts.append(f" - {degree} {major}".strip())
                        context_parts.append("\n")

        # If parsed data is not available, use raw text
        else:
            raw_text = resume_data.get("rawText", "")
            if raw_text:
                context_parts.append("\n**Resume Content**:\n")
                # Limit raw text length
                text_preview = str(raw_text)[:2000]
                if len(str(raw_text)) > 2000:
                    text_preview += "\n... (truncated)"
                context_parts.append(text_preview)

        context_parts.append("\n**Interview Guidance**:\n")
        context_parts.append("- Use this resume information to personalize questions\n")
        context_parts.append("- Probe deeper into mentioned projects and skills\n")
        context_parts.append("- Verify claims with specific follow-up questions\n")
        context_parts.append("- Focus on technologies and experience relevant to the position\n")

        return "".join(context_parts)


def create_resume_analyzer_adapter(settings: Dict[str, Any]) -> ResumeAnalyzerAdapter:
    """Factory function to create resume analyzer adapter."""
    return ResumeAnalyzerAdapter(settings)
