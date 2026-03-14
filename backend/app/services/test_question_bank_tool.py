"""Unit tests for Question Bank Tool Adapter.

These tests validate the integration with the question bank RAG service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.interview_orchestrator import QuestionBankAdapter, ToolExecutionContext


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return {
        "tools": {
            "providers": {
                "question_bank": {
                    "enabled": True,
                    "mode": "url",
                    "url": "http://localhost:8004/api",
                    "timeout_seconds": 5,
                    "headers": {},
                }
            }
        }
    }


@pytest.fixture
def question_bank_adapter(mock_settings):
    """Create a question bank adapter for testing."""
    return QuestionBankAdapter(mock_settings)


@pytest.fixture
def sample_context():
    """Create a sample tool execution context."""
    return ToolExecutionContext(
        trace_id="test-trace-001",
        interview_id=123,
        stage="technical_questions",
        trigger="stage_enter",
        interview_config={
            "candidate_name": "张三",
            "position": "java_backend",
            "difficulty_level": "3",
            "skills": ["Spring", "Redis", "MySQL"],
            "experience_level": "中级",
        },
        conversation_slice=[
            {"role": "assistant", "content": "请介绍一下你的Spring经验。", "metadata": {"question_id": 1}},
            {"role": "user", "content": "我有3年Spring开发经验。"},
        ],
        current_user_message="我有3年Spring开发经验。",
        progress_info={"assessments": [{"question_id": 1, "score": 8}]},
    )


class TestQuestionBankAdapter:
    """Test cases for QuestionBankAdapter."""

    def test_adapter_initialization(self, question_bank_adapter):
        """Test adapter initialization."""
        assert question_bank_adapter.tool_name == "question_bank"
        assert "technical_questions" in question_bank_adapter.supported_stages
        assert "stage_enter" in question_bank_adapter.supported_triggers
        assert question_bank_adapter.default_ttl_seconds == 600

    def test_provider_status_ready(self, question_bank_adapter):
        """Test provider status when ready."""
        status = question_bank_adapter.provider_status()
        assert status["reason"] == "ready"
        assert status["enabled"] is True
        assert status["url"] == "http://localhost:8004/api"

    def test_provider_status_disabled(self, mock_settings):
        """Test provider status when disabled."""
        mock_settings["tools"]["providers"]["question_bank"]["enabled"] = False
        adapter = QuestionBankAdapter(mock_settings)
        status = adapter.provider_status()
        assert status["reason"] == "provider_disabled"
        assert status["enabled"] is False

    def test_map_position(self, question_bank_adapter):
        """Test position mapping."""
        assert question_bank_adapter._map_position("java") == "java_backend"
        assert question_bank_adapter._map_position("Java Backend") == "java_backend"
        assert question_bank_adapter._map_position("frontend") == "web_frontend"
        assert question_bank_adapter._map_position("algorithm") == "algorithm"
        assert question_bank_adapter._map_position("unknown") == "java_backend"  # default

    def test_build_params_basic(self, question_bank_adapter, sample_context):
        """Test basic parameter building."""
        params = question_bank_adapter.build_params(sample_context)

        assert params["position"] == "java_backend"
        assert params["type"] == "technical"  # from technical_questions stage
        assert params["difficulty"] == 3
        assert params["tags"] == "Spring,Redis,MySQL"

    def test_build_context_key_stage_enter(self, question_bank_adapter, sample_context):
        """Test context key for stage_enter trigger."""
        sample_context.trigger = "stage_enter"
        key = question_bank_adapter.build_context_key(sample_context)

        assert key.startswith("questions:technical_questions:")
        assert "java_backend" in key
        assert "3" in key

    def test_build_context_key_user_message(self, question_bank_adapter, sample_context):
        """Test context key for user_message trigger."""
        sample_context.trigger = "user_message"
        key = question_bank_adapter.build_context_key(sample_context)

        assert key.startswith("followup:technical_questions:")
        assert len(key.split(":")) == 3  # followup:stage:hash

    def test_build_search_request(self, question_bank_adapter, sample_context):
        """Test search request building."""
        sample_context.trigger = "stage_enter"
        request = question_bank_adapter.build_request(sample_context)

        assert request["method"] == "GET"
        assert "/question/search" in request["url"]
        assert request["params"]["position"] == "java_backend"
        assert request["params"]["type"] == "technical"
        assert request["params"]["size"] == 5

    def test_build_followup_request(self, question_bank_adapter, sample_context):
        """Test follow-up request building."""
        sample_context.trigger = "user_message"
        request = question_bank_adapter.build_request(sample_context)

        assert request["method"] == "GET"
        assert "/followup" in request["url"]
        assert "1" in request["url"]  # question_id from conversation

    def test_extract_last_question_id(self, question_bank_adapter, sample_context):
        """Test extraction of last question ID."""
        qid = question_bank_adapter._extract_last_question_id(sample_context)
        assert qid == 1

    def test_get_asked_question_ids(self, question_bank_adapter, sample_context):
        """Test extraction of asked question IDs."""
        ids = question_bank_adapter._get_asked_question_ids(sample_context)
        assert ids == [1]

    def test_extract_assessment_scores(self, question_bank_adapter, sample_context):
        """Test extraction of assessment scores."""
        scores = question_bank_adapter._extract_assessment_scores(sample_context)
        assert scores["question_id"] == 1
        assert scores["score"] == 8

    @patch('requests.get')
    def test_call_question_search_success(self, mock_get, question_bank_adapter):
        """Test successful question search API call."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": 1,
                    "code": "java_spring_001",
                    "position": "java_backend",
                    "type": "technical",
                    "text": "Spring Bean的生命周期是怎样的？",
                    "difficulty": 3,
                    "tags": ["Spring", "IOC", "Bean"],
                    "keyPoints": ["BeanDefinition解析", "实例化", "属性填充"],
                    "referenceAnswer": "Spring Bean的生命周期主要包括...",
                    "followUpHints": ["BeanPostProcessor的作用？"],
                    "usedCount": 5,
                    "avgScore": 7.2,
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        payload = {
            "method": "GET",
            "url": "http://localhost:8004/api/question/search",
            "params": {"position": "java_backend", "type": "technical"},
        }

        result = question_bank_adapter.call(payload, timeout_seconds=5)

        assert result.status == "success"
        assert "questions" in result.structured_payload
        assert result.structured_payload["questions"][0]["id"] == 1
        assert "Spring Bean的生命周期" in result.summary

    @patch('requests.get')
    def test_call_followup_success(self, mock_get, question_bank_adapter):
        """Test successful follow-up hints API call."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "code": 200,
            "data": {
                "followUpHints": [
                    "BeanPostProcessor在哪个阶段介入？",
                    "循环依赖是怎么解决的？",
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        payload = {
            "method": "GET",
            "url": "http://localhost:8004/api/question/1/followup",
            "params": {},
        }

        result = question_bank_adapter.call(payload, timeout_seconds=5)

        assert result.status == "success"
        assert "hints" in result.structured_payload
        assert len(result.structured_payload["hints"]) == 2
        assert "BeanPostProcessor" in result.summary

    @patch('requests.get')
    def test_call_timeout(self, mock_get, question_bank_adapter):
        """Test API timeout handling."""
        mock_get.side_effect = MagicMock(side_effect=Exception("Timeout"))

        payload = {
            "method": "GET",
            "url": "http://localhost:8004/api/question/search",
            "params": {},
        }

        result = question_bank_adapter.call(payload, timeout_seconds=1)

        assert result.status in ["error", "timeout"]
        assert len(result.errors) > 0

    def test_parse_question_list(self, question_bank_adapter):
        """Test parsing question list response."""
        questions = [
            {
                "id": 1,
                "code": "java_spring_001",
                "text": "Spring Bean的生命周期是怎样的？",
                "difficulty": 3,
                "tags": ["Spring", "IOC"],
                "keyPoints": ["实例化", "初始化"],
            }
        ]

        result = question_bank_adapter._parse_question_list(questions, 150)

        assert result.status == "success"
        assert result.structured_payload["count"] == 1
        assert "Spring Bean的生命周期" in result.summary
        assert len(result.prompt_context) > 0

    def test_parse_followup_hints(self, question_bank_adapter):
        """Test parsing follow-up hints response."""
        data = {
            "followUpHints": [
                "BeanPostProcessor在哪个阶段介入？",
                "循环依赖是怎么解决的？",
            ]
        }

        result = question_bank_adapter._parse_followup_hints(data, 100)

        assert result.status == "success"
        assert result.structured_payload["hint_count"] == 2
        assert "BeanPostProcessor" in result.summary

    def test_parse_knowledge_documents(self, question_bank_adapter):
        """Test parsing knowledge documents (RAG) response."""
        documents = [
            {
                "id": 1,
                "title": "Redis核心数据结构",
                "content": "# Redis核心数据结构\n\n## String\n...",
                "tags": ["Redis", "数据结构"],
            }
        ]

        result = question_bank_adapter._parse_knowledge_documents(documents, 200)

        assert result.status == "success"
        assert result.structured_payload["doc_count"] == 1
        assert "Redis核心数据结构" in result.summary
        assert len(result.prompt_context) > 0

    def test_hash_conversation(self, question_bank_adapter):
        """Test conversation hashing for cache keys."""
        messages = [
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Hi there"},
        ]

        hash1 = question_bank_adapter._hash_conversation(messages)
        hash2 = question_bank_adapter._hash_conversation(messages)

        # Same conversation should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 8  # MD5 hash, first 8 chars

    def test_is_enabled(self, question_bank_adapter):
        """Test adapter enabled status."""
        assert question_bank_adapter.is_enabled() is True

    def test_build_question_prompt_context(self, question_bank_adapter):
        """Test building prompt context from questions."""
        questions = [
            {
                "id": 1,
                "code": "Q001",
                "text": "What is Spring?",
                "difficulty": 2,
                "tags": ["Spring"],
                "keyPoints": ["IOC", "AOP"],
            }
        ]

        context = question_bank_adapter._build_question_prompt_context(questions)

        assert "Available Questions" in context
        assert "What is Spring?" in context
        assert "IOC" in context
        assert "Spring" in context


class TestQuestionBankIntegration:
    """Integration tests for question bank adapter."""

    def test_full_search_workflow(self, question_bank_adapter, sample_context):
        """Test complete search workflow."""
        # Build request
        sample_context.trigger = "stage_enter"
        request = question_bank_adapter.build_request(sample_context)

        # Verify request structure
        assert request["method"] == "GET"
        assert request["params"]["position"] == "java_backend"
        assert request["params"]["tags"] == "Spring,Redis,MySQL"

    def test_full_followup_workflow(self, question_bank_adapter, sample_context):
        """Test complete follow-up workflow."""
        # Build request
        sample_context.trigger = "user_message"
        request = question_bank_adapter.build_request(sample_context)

        # Verify request structure
        assert request["method"] == "GET"
        assert "/followup" in request["url"]

    def test_different_stages(self, question_bank_adapter, sample_context):
        """Test behavior for different interview stages."""
        stages = [
            ("technical_questions", "technical"),
            ("behavioral_questions", "behavioral"),
            ("project_discussion", "project"),
            ("scenario_analysis", "scenario"),
        ]

        for stage, expected_type in stages:
            sample_context.stage = stage
            params = question_bank_adapter.build_params(sample_context)
            assert params["type"] == expected_type, f"Failed for stage {stage}"


def test_create_question_bank_adapter(mock_settings):
    """Test factory function."""
    from app.services.question_bank_adapter_standalone import create_question_bank_adapter
    adapter = create_question_bank_adapter(mock_settings)
    assert isinstance(adapter, QuestionBankAdapter)
    assert adapter.tool_name == "question_bank"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])