"""Unit tests for resume analyzer adapter.

This module contains unit tests for the ResumeAnalyzerAdapter class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.resume_analyzer_adapter import ResumeAnalyzerAdapter
from app.services.interview_orchestrator import ToolExecutionContext, ToolResult


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return {
        "tools": {
            "providers": {
                "resume_analyzer": {
                    "enabled": True,
                    "mode": "url",
                    "url": "http://localhost:8003/api/growth",
                    "timeout_seconds": 5.0,
                    "headers": {},
                }
            },
            "tool_prompts": {
                "resume_analyzer": {
                    "context_label": "候选人简历分析",
                    "result_prompt_template": "{{ raw_prompt_context }}",
                }
            },
        }
    }


@pytest.fixture
def adapter(mock_settings):
    """Create adapter instance for testing."""
    return ResumeAnalyzerAdapter(mock_settings)


@pytest.fixture
def sample_context():
    """Create sample tool execution context."""
    return ToolExecutionContext(
        trace_id="test-trace-001",
        interview_id=1,
        stage="welcome",
        trigger="interview_start",
        interview_config={
            "candidate_name": "张三",
            "user_id": 1,
            "candidate_id": 1,
            "position": "java_backend",
            "skill_domain": "后端开发",
            "skills": ["Java", "Spring Boot", "MySQL"],
        },
        conversation_slice=[],
        current_user_message=None,
        progress_info=None,
    )


class TestResumeAnalyzerAdapter:
    """Test suite for ResumeAnalyzerAdapter."""

    def test_tool_metadata(self, adapter):
        """Test tool metadata is correctly set."""
        assert adapter.tool_name == "resume_analyzer"
        assert "welcome" in adapter.supported_stages
        assert "technical_questions" in adapter.supported_stages
        assert "interview_start" in adapter.supported_triggers
        assert adapter.default_ttl_seconds == 1800

    def test_provider_status(self, adapter):
        """Test provider status check."""
        status = adapter.provider_status()
        assert status["reason"] == "ready"
        assert status["enabled"] is True
        assert status["mode"] == "url"
        assert status["url"] == "http://localhost:8003/api/growth"

    def test_is_enabled(self, adapter):
        """Test adapter enabled check."""
        assert adapter.is_enabled() is True

    def test_build_context_key_interview_start(self, adapter, sample_context):
        """Test context key building for interview start."""
        key = adapter.build_context_key(sample_context)
        assert key == "resume:1:1:initial"

    def test_build_context_key_stage_enter(self, adapter):
        """Test context key building for stage enter."""
        context = ToolExecutionContext(
            trace_id="test-trace-002",
            interview_id=1,
            stage="technical_questions",
            trigger="stage_enter",
            interview_config={"user_id": 1},
        )
        key = adapter.build_context_key(context)
        assert key == "resume:1:1:technical_questions"

    def test_build_params(self, adapter, sample_context):
        """Test parameter building."""
        params = adapter.build_params(sample_context)
        assert params["userId"] == 1
        assert params["position"] == "java_backend"
        assert params["skillDomain"] == "后端开发"
        assert "Java" in params["skills"]

    def test_build_request_interview_start(self, adapter, sample_context):
        """Test request building for interview start."""
        request = adapter.build_request(sample_context)
        assert request["method"] == "GET"
        assert "/resume/list" in request["url"]
        assert request["params"]["userId"] == 1
        assert request["follow_up"] == "get_resume_detail"

    @patch("requests.get")
    def test_call_success_resume_list(self, mock_get, adapter, sample_context):
        """Test successful API call for resume list."""
        # Mock response for resume list
        mock_list_response = Mock()
        mock_list_response.json.return_value = {
            "code": 200,
            "message": "Found 1 resume(s)",
            "data": [
                {
                    "id": 1,
                    "userId": 1,
                    "fileName": "test_resume.pdf",
                    "parseStatus": "DONE",
                }
            ],
        }
        mock_list_response.raise_for_status = Mock()

        # Mock response for resume detail
        mock_detail_response = Mock()
        mock_detail_response.json.return_value = {
            "code": 200,
            "message": "Resume retrieved successfully",
            "data": {
                "id": 1,
                "fileName": "test_resume.pdf",
                "parseStatus": "DONE",
                "parsedJson": {
                    "basics": {"name": "张三", "email": "test@example.com"},
                    "skills": ["Java", "Spring Boot"],
                    "projects": [
                        {
                            "name": "Test Project",
                            "role": "Developer",
                            "description": "A test project",
                        }
                    ],
                },
            },
        }
        mock_detail_response.raise_for_status = Mock()

        mock_get.side_effect = [mock_list_response, mock_detail_response]

        payload = {
            "method": "GET",
            "url": "http://localhost:8003/api/growth/resume/list",
            "params": {"userId": 1},
            "follow_up": "get_resume_detail",
        }

        result = adapter.call(payload, timeout_seconds=5.0)

        assert result.status == "success"
        assert "test_resume.pdf" in result.summary
        assert "Java" in result.prompt_context

    @patch("requests.get")
    def test_call_timeout(self, mock_get, adapter, sample_context):
        """Test API call timeout handling."""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("Request timeout")

        payload = {
            "method": "GET",
            "url": "http://localhost:8003/api/growth/resume/list",
            "params": {"userId": 1},
        }

        result = adapter.call(payload, timeout_seconds=5.0)

        assert result.status == "timeout"
        assert len(result.errors) > 0

    @patch("requests.get")
    def test_call_http_error(self, mock_get, adapter, sample_context):
        """Test API call HTTP error handling."""
        from requests.exceptions import HTTPError

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        payload = {
            "method": "GET",
            "url": "http://localhost:8003/api/growth/resume/list",
            "params": {"userId": 1},
        }

        result = adapter.call(payload, timeout_seconds=5.0)

        assert result.status == "error"
        assert len(result.errors) > 0

    def test_parse_resume_list_empty(self, adapter):
        """Test parsing empty resume list."""
        body = {"code": 200, "message": "No resumes found", "data": []}
        result = adapter._parse_resume_list(body, 100)

        assert result.status == "success"
        assert "No resumes found" in result.summary
        assert result.structured_payload["count"] == 0

    def test_parse_resume_detail_success(self, adapter):
        """Test parsing resume detail successfully."""
        body = {
            "code": 200,
            "message": "Success",
            "data": {
                "id": 1,
                "fileName": "test.pdf",
                "parseStatus": "DONE",
                "parsedJson": {
                    "skills": ["Java", "Python"],
                    "projects": [
                        {
                            "name": "Project A",
                            "role": "Developer",
                            "technologies": ["Spring", "MySQL"],
                        }
                    ],
                },
            },
        }

        result = adapter._parse_resume_detail(body, 150)

        assert result.status == "success"
        assert "test.pdf" in result.summary
        assert "Java" in result.summary
        assert "Project A" in result.summary
        assert result.structured_payload["parseStatus"] == "DONE"

    def test_build_resume_prompt_context(self, adapter):
        """Test building prompt context from resume."""
        resume_data = {
            "fileName": "test_resume.pdf",
            "parsedJson": {
                "skills": ["Java", "Spring Boot", "MySQL"],
                "projects": [
                    {
                        "name": "E-commerce Platform",
                        "role": "Backend Developer",
                        "description": "Built scalable e-commerce backend",
                        "technologies": ["Java", "Spring Cloud", "Redis"],
                    }
                ],
                "workExperience": [
                    {
                        "company": "Tech Corp",
                        "position": "Senior Developer",
                        "duration": "2020-2023",
                    }
                ],
                "education": [
                    {
                        "school": "University of Technology",
                        "degree": "Bachelor",
                        "major": "Computer Science",
                    }
                ],
            },
        }

        context = adapter._build_resume_prompt_context(resume_data)

        assert "Candidate Resume Analysis" in context
        assert "test_resume.pdf" in context
        assert "Java" in context
        assert "E-commerce Platform" in context
        assert "Tech Corp" in context
        assert "University of Technology" in context
        assert "Interview Guidance" in context

    def test_build_resume_prompt_context_raw_text(self, adapter):
        """Test building prompt context when parsed data is not available."""
        resume_data = {
            "fileName": "unparsed_resume.pdf",
            "rawText": "John Doe\nSoftware Engineer\nExperience with Java and Python",
            "parsedJson": None,
        }

        context = adapter._build_resume_prompt_context(resume_data)

        assert "Resume Content" in context
        assert "John Doe" in context
        assert "Software Engineer" in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
