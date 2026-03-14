"""Integration test script for Question Bank Tool Adapter.

This script tests the actual connection to the question bank service
and verifies the integration works correctly.
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.interview_orchestrator import QuestionBankAdapter, ToolExecutionContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_question_bank_integration():
    """Test the question bank integration."""

    # Mock settings for testing
    settings = {
        "tools": {
            "providers": {
                "question_bank": {
                    "enabled": True,
                    "mode": "url",
                    "url": "http://localhost:8004/api",
                    "timeout_seconds": 10,
                    "headers": {},
                }
            }
        }
    }

    # Create adapter
    adapter = QuestionBankAdapter(settings)
    logger.info(f"Created adapter: {adapter.tool_name}")
    logger.info(f"Supported stages: {adapter.supported_stages}")
    logger.info(f"Supported triggers: {adapter.supported_triggers}")

    # Check provider status
    status = adapter.provider_status()
    logger.info(f"Provider status: {status}")

    if not adapter.is_enabled():
        logger.error("Question bank adapter is not enabled!")
        return False

    # Test 1: Question Search
    logger.info("\n=== Test 1: Question Search ===")
    context = ToolExecutionContext(
        trace_id="test-trace-001",
        interview_id=123,
        stage="technical_questions",
        trigger="stage_enter",
        interview_config={
            "candidate_name": "测试候选人",
            "position": "java_backend",
            "difficulty_level": "3",
            "skills": ["Spring", "Redis", "MySQL"],
            "experience_level": "中级",
        },
        conversation_slice=[],
        current_user_message=None,
        progress_info=None,
    )

    try:
        request = adapter.build_request(context)
        logger.info(f"Request URL: {request['url']}")
        logger.info(f"Request params: {json.dumps(request['params'], ensure_ascii=False)}")

        result = adapter.call(request, timeout_seconds=10)
        logger.info(f"Result status: {result.status}")
        logger.info(f"Result summary: {result.summary}")
        logger.info(f"Questions found: {result.structured_payload.get('count', 0)}")

        if result.status == "success" and result.structured_payload.get("questions"):
            questions = result.structured_payload["questions"]
            logger.info(f"✓ Successfully retrieved {len(questions)} questions")
            for i, q in enumerate(questions[:3], 1):
                logger.info(f"  {i}. [{q.get('code')}] {q.get('text')} (难度: {q.get('difficulty')})")
        else:
            logger.error(f"✗ Question search failed: {result.errors}")

    except Exception as e:
        logger.error(f"✗ Question search error: {e}")
        return False

    # Test 2: Follow-up Hints
    logger.info("\n=== Test 2: Follow-up Hints ===")
    context_with_qid = ToolExecutionContext(
        trace_id="test-trace-002",
        interview_id=123,
        stage="technical_questions",
        trigger="user_message",
        interview_config={
            "position": "java_backend",
        },
        conversation_slice=[
            {"role": "assistant", "content": "Spring Bean的生命周期是怎样的？", "metadata": {"question_id": 1}},
            {"role": "user", "content": "Spring Bean的生命周期包括实例化、属性填充、初始化等阶段。"},
        ],
        current_user_message="Spring Bean的生命周期包括实例化、属性填充、初始化等阶段。",
        progress_info=None,
    )

    try:
        request = adapter.build_request(context_with_qid)
        logger.info(f"Request URL: {request['url']}")

        result = adapter.call(request, timeout_seconds=10)
        logger.info(f"Result status: {result.status}")
        logger.info(f"Result summary: {result.summary}")

        if result.status == "success" and result.structured_payload.get("hints"):
            hints = result.structured_payload["hints"]
            logger.info(f"✓ Successfully retrieved {len(hints)} follow-up hints")
            for i, hint in enumerate(hints, 1):
                logger.info(f"  {i}. {hint}")
        else:
            logger.warning(f"! No follow-up hints available or request failed")

    except Exception as e:
        logger.error(f"✗ Follow-up hints error: {e}")

    # Test 3: Knowledge Search (RAG)
    logger.info("\n=== Test 3: Knowledge Document Search (RAG) ===")

    # Direct API call to test knowledge search
    try:
        import requests

        knowledge_url = "http://localhost:8004/api/knowledge/search"
        params = {
            "query": "Redis缓存",
            "position": "java_backend",
            "size": 3,
        }

        logger.info(f"Knowledge search URL: {knowledge_url}")
        logger.info(f"Params: {json.dumps(params, ensure_ascii=False)}")

        response = requests.get(knowledge_url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.info(f"Response code: {data.get('code')}")

        if data.get("code") == 200:
            documents = data.get("data", [])
            logger.info(f"✓ Successfully retrieved {len(documents)} knowledge documents")

            for i, doc in enumerate(documents[:2], 1):
                logger.info(f"  {i}. {doc.get('title')} (tags: {', '.join(doc.get('tags', []))})")
        else:
            logger.error(f"✗ Knowledge search failed: {data.get('message')}")

    except Exception as e:
        logger.error(f"✗ Knowledge search error: {e}")

    logger.info("\n=== Integration Test Complete ===")
    return True


def test_context_key_generation():
    """Test context key generation for caching."""
    settings = {
        "tools": {
            "providers": {
                "question_bank": {
                    "enabled": True,
                    "url": "http://localhost:8004/api",
                }
            }
        }
    }

    adapter = QuestionBankAdapter(settings)

    # Test different contexts
    contexts = [
        ("stage_enter", "technical_questions"),
        ("user_message", "technical_questions"),
        ("interview_end", "technical_questions"),
    ]

    logger.info("=== Context Key Generation Test ===")
    for trigger, stage in contexts:
        context = ToolExecutionContext(
            trace_id="test",
            interview_id=123,
            stage=stage,
            trigger=trigger,
            interview_config={"position": "java_backend"},
            conversation_slice=[],
        )
        key = adapter.build_context_key(context)
        logger.info(f"{trigger:20} + {stage:20} → {key}")

    return True


if __name__ == "__main__":
    logger.info("Starting Question Bank Integration Tests")
    logger.info("=" * 50)

    try:
        # Test context key generation first (doesn't require service)
        test_context_key_generation()

        # Test actual integration (requires running service)
        success = test_question_bank_integration()

        if success:
            logger.info("\n✓ All tests completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n✗ Some tests failed!")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)