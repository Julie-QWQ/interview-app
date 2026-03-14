"""Standalone Question Bank Adapter - Use this if you need to import the adapter separately.

This module provides a standalone version of the Question Bank adapter that can be
imported without circular dependencies. The main implementation is now in
interview_orchestrator.py as QuestionBankAdapter.

Note: This file is kept for reference and testing purposes.
"""

# For standalone usage, you can import the adapter from interview_orchestrator:
# from app.services.interview_orchestrator import QuestionBankAdapter

# Or use the factory function:
def create_question_bank_adapter(settings):
    """Factory function to create question bank adapter."""
    from app.services.interview_orchestrator import QuestionBankAdapter
    return QuestionBankAdapter(settings)


__all__ = ['create_question_bank_adapter']