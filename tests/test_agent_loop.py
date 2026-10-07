"""Tests for Loop 1: Agent Loop."""
import pytest
from unittest.mock import Mock, patch

from src.loops.agent_loop import AgentLoop
from src.models.review_models import ReviewResult


class TestAgentLoop:
    """Test suite for Agent Loop (Loop 1)."""

    @patch('src.loops.agent_loop.ChatOpenAI')
    def test_agent_loop_initialization(self, mock_llm):
        """Test that agent loop initializes correctly."""
        agent_loop = AgentLoop(prompt_version="base")

        assert agent_loop.prompt_version == "base"
        assert agent_loop.llm is not None
        assert len(agent_loop.tools) == 9  # Should have 9 tools
        assert agent_loop.agent is not None

    @patch('src.loops.agent_loop.ChatOpenAI')
    @patch('src.loops.agent_loop.AgentExecutor')
    def test_review_code_returns_result(self, mock_executor, mock_llm):
        """Test that review_code returns a ReviewResult."""
        # Mock agent response
        mock_agent = Mock()
        mock_agent.invoke.return_value = {
            'output': 'Test review output',
            'intermediate_steps': []
        }
        mock_executor.return_value = mock_agent

        agent_loop = AgentLoop()
        result, metrics = agent_loop.review_code(git_diff="test diff")

        assert isinstance(result, ReviewResult)
        assert isinstance(metrics, dict)
        assert 'duration' in metrics
        assert 'tools_used' in metrics

    def test_extract_issues_from_output(self):
        """Test issue extraction from agent output."""
        agent_loop = AgentLoop()

        output = """
        Found issues in test.py:
        Line 10: Critical security vulnerability - SQL injection detected
        Line 25: Major error - Division by zero possible
        """

        issues = agent_loop._extract_issues_from_output(output)

        assert len(issues) > 0
        # Check that at least one issue was extracted

    def test_generate_summary(self):
        """Test summary generation."""
        agent_loop = AgentLoop()

        from src.models.review_models import Issue

        issues = [
            Issue(
                file="test.py",
                line=10,
                severity="critical",
                category="security",
                description="SQL injection",
                suggestion="Use parameterized queries",
            ),
            Issue(
                file="test.py",
                line=20,
                severity="minor",
                category="style",
                description="Missing docstring",
                suggestion="Add docstring",
            ),
        ]

        summary = agent_loop._generate_summary("output", issues)

        assert "2 issue" in summary
        assert "critical" in summary or "1 critical" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
