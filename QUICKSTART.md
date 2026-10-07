# Quick Start Guide - Loop Engineering POC

## 1. Setup (5 minutes)

### Install Dependencies
```bash
cd loop_eng
pip install -r requirements.txt
```

### Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-...
```

### Initialize
```bash
python -m src.main init
```

Expected output:
```
✅ Directories created
✅ Prompts loaded
🎉 Initialization complete!
```

---

## 2. Quick Demo (2 minutes)

Run the automated demo:
```bash
python -m src.main demo
```

This will:
1. Create a sample Python file with security issues
2. Initialize git if needed
3. Run a full code review
4. Show all 4 loops in action

**Expected output:**
```
[Loop 3] 🎯 Event: demo triggered
[Loop 2] 🔍 Verification Loop - Starting
[Loop 1] 🤖 Agent Loop - Starting code review
[Loop 2] 📊 Quality Score: 82/100 ✅ PASSED
📋 Review Results (with issues found)
📈 Metrics
```

---

## 3. Try It on Your Code (5 minutes)

### Step 1: Make Changes
Edit or create a Python file:
```bash
cat > my_code.py << 'EOF'
def unsafe_query(user_input):
    # SQL injection vulnerability
    return f"SELECT * FROM users WHERE id={user_input}"

def divide(a, b):
    # Missing error handling
    return a / b

password = "hardcoded123"  # Hardcoded secret
EOF
```

### Step 2: Stage Changes
```bash
git add my_code.py
```

### Step 3: Review
```bash
python -m src.main review
```

You'll see:
- **Loop 1** analyzes your code with tools (pylint, security checks, AST)
- **Loop 2** grades the review quality
- If quality is low (< 70/100), it retries with feedback
- Beautiful formatted results with issues grouped by severity

---

## 4. Trigger Self-Improvement (Loop 4)

### Run 5 Reviews
```bash
# Make 5 different changes and review each
echo "# Change 1" >> my_code.py && git add my_code.py && python -m src.main review
echo "# Change 2" >> my_code.py && git add my_code.py && python -m src.main review
echo "# Change 3" >> my_code.py && git add my_code.py && python -m src.main review
echo "# Change 4" >> my_code.py && git add my_code.py && python -m src.main review
echo "# Change 5" >> my_code.py && git add my_code.py && python -m src.main review
```

On the 5th review, **Loop 4 automatically triggers**:
```
[Loop 3] 🔄 Triggering self-improvement analysis...
```

### Or Trigger Manually
```bash
python -m src.main improve
```

Expected output:
```
[Loop 4] 🧠 Hill Climbing Loop - Analyzing last 10 reviews
[Loop 4] 📊 Current Metrics:
  • Avg Quality Score: 72.5/100
  • Avg Retry Count: 1.3
[Loop 4] 🎯 Identifying improvement opportunities...
[Loop 4] 🔧 Generating improvements...
[Loop 4] 🚀 Promoting new prompt!
```

---

## 5. View Stats

```bash
python -m src.main stats
```

Shows:
- Total reviews
- Average quality score
- Average retry count
- Top issue categories
- Improvement trends

---

## Understanding the Output

### Loop Indicators
- `[Loop 1]` - Agent analyzing code with tools
- `[Loop 2]` - Quality verification
- `[Loop 3]` - Event orchestration
- `[Loop 4]` - Self-improvement

### Quality Scores
- **0-49**: Poor (will retry)
- **50-69**: Below threshold (will retry)
- **70-84**: Passed
- **85-100**: Excellent

### Issue Severity
- 🔴 **Critical**: Security vulnerabilities, bugs that crash
- 🟠 **Major**: Logic errors, missing error handling
- 🟡 **Minor**: Style issues, minor improvements
- ℹ️ **Info**: Suggestions, optimizations

---

## Common Commands

```bash
# Run a review
python -m src.main review

# Trigger improvement
python -m src.main improve

# View stats dashboard
python -m src.main stats

# Show specific trace
python -m src.main show-trace <trace-id>

# Run demo
python -m src.main demo
```

---

## What to Expect

### First Review (Cold Start)
- Finds issues in your code
- Quality: ~65-75/100
- May retry 1-2 times
- Takes 15-30 seconds

### After 5 Reviews (Loop 4 Triggered)
- System analyzes patterns
- Identifies weaknesses (e.g., "missing security checks")
- Generates improved prompt
- Promotes if better

### Subsequent Reviews
- Uses optimized prompt
- Higher quality scores (~80-90/100)
- Fewer retries (~0.5 avg)
- **System has improved itself!**

---

## Troubleshooting

### "No changes detected"
```bash
# Make sure files are staged
git add your_file.py

# Or check what's changed
git status
```

### "OPENAI_API_KEY not set"
```bash
# Edit .env file
nano .env

# Add your key
OPENAI_API_KEY=sk-your-key-here
```

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Run from project root
cd loop_eng
python -m src.main review
```

### ModuleNotFoundError
```bash
# Make sure you're in the project directory
cd /Users/habilash/Desktop/loop_eng

# Use python -m to run
python -m src.main review
```

---

## Next Steps

1. **Experiment with different code**: Try various Python files to see different issues detected

2. **Watch Loop 4 improve**: Run 10+ reviews and observe quality scores increasing

3. **Extend the tools**: Add new analysis tools in `src/tools/`

4. **Customize prompts**: Edit `data/prompts/base_prompts.json`

5. **Integrate with CI/CD**: Add as pre-commit hook or GitHub Action

---

## Demo Presentation Flow (5 minutes)

For stakeholders:

1. **Show the concept** (1 min)
   - Explain 4 loops briefly

2. **Run demo** (2 min)
   - `python -m src.main demo`
   - Point out each loop's activity in output

3. **Show improvement** (2 min)
   - Show before/after metrics from stats
   - Explain how Loop 4 improved the system

**Key message**: "The system learns and improves itself through loop engineering"

---

## Success Indicators

✅ All loops clearly visible in output  
✅ Quality grading working (retries when needed)  
✅ Loop 4 triggers and generates improvements  
✅ Metrics show improvement over time  
✅ Rich formatted output with colors/emojis  

---

**Ready?** Start with `python -m src.main demo` 🚀
