"""Loop 1: Agent Loop - Core LangChain agent with tool calling."""
import json
import time
from pathlib import Path
from typing import Dict, Any, List

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage, HumanMessage

from src.config import settings
from src.models.review_models import ReviewResult, Issue
from src.tools.git_tools import get_git_diff, get_changed_files, get_file_content
from src.tools.linter_tools import run_pylint, run_flake8
from src.tools.ast_tools import parse_ast, check_complexity
from src.tools.static_analysis import check_security, check_imports


class AgentLoop:
    """Loop 1: LangChain agent that uses tools to review code."""

    def __init__(self, prompt_version: str = "base"):
        """
        Initialize the agent loop.

        Args:
            prompt_version: Version of the prompt to use (base or optimized)
        """
        self.prompt_version = prompt_version
        self.llm = ChatOpenAI(
            model=settings.model_name,
            temperature=0,
            api_key=settings.openai_api_key,
        )

        # Load prompt
        self.system_prompt = self._load_prompt(prompt_version)

        # Define tools
        self.tools = [
            get_git_diff,
            get_changed_files,
            get_file_content,
            run_pylint,
            run_flake8,
            parse_ast,
            check_complexity,
            check_security,
            check_imports,
        ]

        # Create agent
        self.agent = self._create_agent()

    def _load_prompt(self, version: str) -> str:
        """Load prompt from JSON file."""
        prompt_file = settings.prompts_dir / "base_prompts.json"
        optimized_file = settings.prompts_dir / "optimized_prompts.json"

        try:
            if version != "base" and optimized_file.exists():
                with open(optimized_file, 'r') as f:
                    prompts = json.load(f)
                    return prompts.get("code_review_prompt", self._load_base_prompt())
            else:
                return self._load_base_prompt()
        except Exception as e:
            print(f"[Loop 1] Warning: Could not load prompt, using default: {e}")
            return self._load_base_prompt()

    def _load_base_prompt(self) -> str:
        """Load base prompt."""
        prompt_file = settings.prompts_dir / "base_prompts.json"
        with open(prompt_file, 'r') as f:
            prompts = json.load(f)
            return prompts["code_review_prompt"]

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=15,
            handle_parsing_errors=True,
        )

        return agent_executor

    def review_code(self, git_diff: str = None, context: Dict[str, Any] = None) -> tuple[ReviewResult, Dict[str, Any]]:
        """
        Perform code review using the agent.

        Args:
            git_diff: Optional pre-fetched git diff
            context: Optional context (e.g., feedback from verification loop)

        Returns:
            Tuple of (ReviewResult, metrics dict)
        """
        print("\n[Loop 1] 🤖 Agent Loop - Starting code review")
        start_time = time.time()

        try:
            # Build input
            if context and context.get('feedback'):
                feedback_text = "\n\nPREVIOUS FEEDBACK TO ADDRESS:\n" + "\n".join(context['feedback'])
                input_text = f"Review the code changes and address the feedback provided.{feedback_text}"
            else:
                input_text = "Review the current code changes. Start by getting the git diff or changed files, then analyze each file."

            # Invoke agent
            print("[Loop 1]   Invoking agent with tools...")
            result = self.agent.invoke({"input": input_text})

            # Extract output
            agent_output = result.get('output', '')
            print(f"[Loop 1]   Agent completed analysis")

            # Parse the output into structured format
            review_result = self._parse_agent_output(agent_output, result)

            # Calculate metrics
            duration = time.time() - start_time
            review_result.duration = duration

            metrics = {
                'tools_used': self._extract_tools_used(result),
                'duration': duration,
                'issues_found': len(review_result.issues),
                'prompt_version': self.prompt_version,
            }

            print(f"[Loop 1] ✅ Review complete: {len(review_result.issues)} issues found in {duration:.2f}s")

            return review_result, metrics

        except Exception as e:
            print(f"[Loop 1] ❌ Error during review: {str(e)}")
            # Return minimal result
            review_result = ReviewResult(
                issues=[],
                summary=f"Error during review: {str(e)}",
                files_reviewed=[],
                tools_used=[],
            )
            metrics = {
                'tools_used': [],
                'duration': time.time() - start_time,
                'issues_found': 0,
                'error': str(e),
            }
            return review_result, metrics

    def _parse_agent_output(self, output: str, agent_result: Dict) -> ReviewResult:
        """
        Parse agent output into structured ReviewResult.

        This is a simplified parser. In production, you'd use structured output.
        """
        # Try to extract issues from the output
        issues = self._extract_issues_from_output(output)

        # Get files that were reviewed
        files_reviewed = self._extract_files_from_intermediate(agent_result)

        # Get tools used
        tools_used = self._extract_tools_used(agent_result)

        return ReviewResult(
            issues=issues,
            summary=self._generate_summary(output, issues),
            files_reviewed=files_reviewed,
            tools_used=tools_used,
        )

    def _extract_issues_from_output(self, output: str) -> List[Issue]:
        """Extract issues from agent output text."""
        issues = []

        # Look for common patterns in output
        lines = output.split('\n')

        current_file = None
        for line in lines:
            line = line.strip()

            # Try to detect file mentions
            if '.py' in line and ('/' in line or 'File' in line):
                # Extract filename
                for word in line.split():
                    if '.py' in word:
                        current_file = word.strip(':').strip()

            # Look for severity indicators
            severity = 'info'
            if any(word in line.lower() for word in ['critical', 'security', 'vulnerability', 'injection']):
                severity = 'critical'
            elif any(word in line.lower() for word in ['error', 'bug', 'major', 'warning']):
                severity = 'major'
            elif any(word in line.lower() for word in ['style', 'convention', 'minor']):
                severity = 'minor'

            # Look for issue descriptions
            if any(indicator in line.lower() for indicator in ['issue:', 'problem:', 'warning:', 'error:', '⚠️', '🔒']):
                description = line

                # Try to extract line number
                line_num = 1
                import re
                line_match = re.search(r'line\s+(\d+)', line, re.IGNORECASE)
                if line_match:
                    line_num = int(line_match.group(1))

                issues.append(Issue(
                    file=current_file or 'unknown',
                    line=line_num,
                    severity=severity,
                    category='general',
                    description=description,
                    suggestion="Review and fix the issue",
                    tool_source="agent_analysis",
                ))

        # If no issues extracted but output mentions findings, create a general issue
        if not issues and len(output) > 100:
            issues.append(Issue(
                file='general',
                line=0,
                severity='info',
                category='general',
                description='Code review completed - see full output',
                suggestion=output[:500],
                tool_source='agent_summary',
            ))

        return issues

    def _generate_summary(self, output: str, issues: List[Issue]) -> str:
        """Generate summary from output and issues."""
        if not issues:
            return "No significant issues found in the code review."

        critical = sum(1 for i in issues if i.severity == 'critical')
        major = sum(1 for i in issues if i.severity == 'major')
        minor = sum(1 for i in issues if i.severity == 'minor')

        summary = f"Found {len(issues)} issue(s): "
        parts = []
        if critical > 0:
            parts.append(f"{critical} critical")
        if major > 0:
            parts.append(f"{major} major")
        if minor > 0:
            parts.append(f"{minor} minor")

        summary += ", ".join(parts)
        return summary

    def _extract_files_from_intermediate(self, agent_result: Dict) -> List[str]:
        """Extract files that were analyzed from intermediate steps."""
        files = set()

        # Look through intermediate steps for file paths
        intermediate_steps = agent_result.get('intermediate_steps', [])
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) >= 2:
                action, observation = step[0], step[1]
                if hasattr(action, 'tool_input'):
                    tool_input = action.tool_input
                    if isinstance(tool_input, dict) and 'file_path' in tool_input:
                        files.add(tool_input['file_path'])
                    elif isinstance(tool_input, str) and '.py' in tool_input:
                        files.add(tool_input)

        return list(files)

    def _extract_tools_used(self, agent_result: Dict) -> List[str]:
        """Extract list of tools that were called."""
        tools = set()

        intermediate_steps = agent_result.get('intermediate_steps', [])
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) >= 1:
                action = step[0]
                if hasattr(action, 'tool'):
                    tools.add(action.tool)

        return list(tools)
