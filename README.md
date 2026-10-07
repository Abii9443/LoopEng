# 🔄 Automated Code Review Assistant - Loop Engineering POC

A proof-of-concept demonstrating **Loop Engineering** - a framework for building sophisticated AI agents by stacking four feedback loops that continuously improve over time.

## What is Loop Engineering?

Loop Engineering (from LangChain) is an approach to building AI agents through nested feedback loops:

1. **Loop 1 - Agent Loop**: Basic LLM + tools execution
2. **Loop 2 - Verification Loop**: Quality grading with retry logic
3. **Loop 3 - Event-Driven Loop**: Automated triggering and orchestration
4. **Loop 4 - Hill Climbing Loop**: Self-improvement through trace analysis

This POC implements all 4 loops for automated Python code review.

## Architecture

```
User triggers review
         ↓
[Loop 3] Event orchestrator
         ↓
[Loop 2] Verification (quality grading)
         ↓ (retry if quality low)
[Loop 1] Agent + Tools (pylint, AST, security checks)
         ↓
Store trace → Every 5th review triggers
         ↓
[Loop 4] Self-improvement (analyze patterns, optimize prompts)
```

## Features

- **Comprehensive Analysis**: Uses multiple tools (pylint, flake8, AST parsing, security checks)
- **Quality Assurance**: Grades each review and retries if below threshold
- **Self-Improving**: Learns from past reviews to optimize prompts
- **Rich Output**: Beautiful terminal output showing each loop's activity
- **Trace Storage**: All reviews stored for analysis and improvement

## Installation

1. **Clone and navigate to the project:**
```bash
cd loop_eng
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

4. **Initialize:**
```bash
python -m src.main init
```

## Usage

### Run a Code Review

```bash
# Make some changes to Python files in a git repo
echo "def unsafe_query(user_input): return f'SELECT * FROM users WHERE id={user_input}'" > test.py
git add test.py

# Run review
python -m src.main review
```

**Output shows all loops in action:**
```
[Loop 3] 🎯 Event: manual_review triggered
[Loop 3] 📝 Extracting git diff...
[Loop 2] 🔍 Verification Loop - Starting
[Loop 1] 🤖 Agent Loop - Starting code review
[Loop 1]   Invoking agent with tools...
[Loop 2]   Grading review quality...
[Loop 2] 📊 Quality Score: 65/100 ⚠️ Below threshold
[Loop 2] 🔄 Retrying (1/3)...
[Loop 1] 🤖 Agent Loop - Retry with feedback
[Loop 2] 📊 Quality Score: 82/100 ✅ PASSED
```

### Trigger Self-Improvement (Loop 4)

```bash
# Manually analyze last 10 reviews
python -m src.main improve --num-traces 10
```

Or wait for automatic trigger (every 5th review).

### View Statistics

```bash
python -m src.main stats
```

### Quick Demo

```bash
# Creates sample file with issues and reviews it
python -m src.main demo
```

## How Each Loop Works

### Loop 1: Agent Loop
- Creates LangChain agent with 9 tools
- Agent decides which tools to use
- Analyzes results and generates structured review
- **Tools**: `get_git_diff`, `run_pylint`, `run_flake8`, `parse_ast`, `check_complexity`, `check_security`, `check_imports`

### Loop 2: Verification Loop
- Takes review from Loop 1
- Grades against rubric (completeness, accuracy, actionability, depth, coverage)
- If score < 70/100: provides feedback and triggers Loop 1 retry
- Max 3 retries
- Returns `VerifiedReview` with quality score

### Loop 3: Event-Driven Loop
- Orchestrates the full review process
- Can be triggered by: CLI command, git hooks, webhooks (future)
- Stores complete trace to JSON
- Displays rich formatted results
- Triggers Loop 4 every Nth review

### Loop 4: Hill Climbing Loop
- Loads last N traces
- Calculates aggregate metrics
- Identifies improvement opportunities:
  - Low quality scores
  - High retry rates
  - Poor tool utilization
  - Missing issue categories
- Uses LLM to generate improved prompts
- A/B tests and promotes if better
- New prompt automatically used in future reviews

## Project Structure

```
loop_eng/
├── src/
│   ├── main.py                  # CLI interface
│   ├── config.py                # Configuration
│   ├── loops/
│   │   ├── agent_loop.py        # Loop 1
│   │   ├── verification_loop.py # Loop 2
│   │   ├── event_loop.py        # Loop 3
│   │   └── hill_climbing_loop.py# Loop 4
│   ├── tools/                   # Code analysis tools
│   ├── agents/                  # LLM agents
│   ├── storage/                 # Trace storage
│   ├── models/                  # Pydantic models
│   └── utils/                   # Display & metrics
├── data/
│   ├── traces/                  # Review traces (JSON)
│   ├── improvements/            # Improvement records
│   └── prompts/                 # Base & optimized prompts
└── tests/                       # Unit tests
```

## Configuration

Edit `.env` to configure:

```bash
OPENAI_API_KEY=your_key_here
MODEL_NAME=gpt-4-turbo-preview
QUALITY_THRESHOLD=70            # Minimum quality score
MAX_RETRIES=3                   # Max retry attempts
IMPROVEMENT_FREQUENCY=5         # Trigger Loop 4 every N reviews
```

## CLI Commands

```bash
# Main review command
python -m src.main review

# Trigger improvement analysis
python -m src.main improve --num-traces 10

# View statistics dashboard
python -m src.main stats

# Show specific trace
python -m src.main show-trace <trace-id>

# Initialize project
python -m src.main init

# Run demo
python -m src.main demo
```

## Example Output

When you run a review, you'll see:

1. **Loop 3** extracts git changes
2. **Loop 2** starts verification
3. **Loop 1** runs analysis with tools
4. **Loop 2** grades quality (may retry)
5. **Results displayed** in rich format with:
   - Issues table (critical → info)
   - Metrics dashboard
   - Quality score
   - Retry count
   - Duration

After 5 reviews:
- **Loop 4** analyzes all traces
- Identifies patterns (e.g., "Reviews lack security depth")
- Generates improved prompt
- A/B tests improvement
- Promotes if better

## Demo Scenario

1. **First Review** (cold start):
   - Finds 3 issues
   - Quality: 65/100, retries once
   - Final: 78/100

2. **Reviews 2-4**:
   - System learns patterns
   - Average quality: 72/100
   - Average retries: 1.2

3. **5th Review triggers Loop 4**:
   - Analyzes patterns
   - "Reviews missing security checks"
   - Generates improved prompt
   - Tests: 83/100 vs baseline 72/100
   - **Promotes new prompt**

4. **Review 6+**:
   - Uses optimized prompt
   - Average quality: 85/100
   - Average retries: 0.4
   - **System improved itself!**

## Testing

```bash
# Run tests
pytest tests/

# Test specific loop
pytest tests/test_agent_loop.py -v
```

## Extending the POC

To add new capabilities:

1. **New Tools**: Add to `src/tools/` and register in `agent_loop.py`
2. **New Triggers**: Add event types in `event_loop.py`
3. **Better Grading**: Enhance rubric in `quality_grader.py`
4. **Advanced A/B Testing**: Implement real testing in `hill_climbing_loop.py`

## Limitations

This is a POC demonstrating loop engineering concepts:

- ✅ Shows all 4 loops clearly
- ✅ Self-improvement mechanism works
- ⚠️ Simplified issue parsing (production would use structured output)
- ⚠️ A/B testing is simulated (production would run real reviews)
- ⚠️ Limited to Python code analysis

## Resources

- [LangChain Loop Engineering Article](https://www.langchain.com/blog/the-art-of-loop-engineering)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

## License

MIT

## Author

Built as a POC for demonstrating loop engineering concepts with Claude Code.

---

**🚀 Ready to see loop engineering in action?**

```bash
python -m src.main demo
```
