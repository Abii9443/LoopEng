# 🚀 Quick Start Guide - Loop Engineering POC

Get the Loop Engineering POC up and running in minutes!

## ⚡ Prerequisites

- Python 3.9 or higher
- 4GB RAM minimum (8GB recommended for faster model loading)
- Internet connection (for first-time model downloads)

## 📦 Installation

### 1. Clone and Navigate

```bash
cd /Users/habilash/Desktop/loop_eng
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- HuggingFace Transformers & models
- PyTorch
- FAISS for vector search
- Rich for beautiful CLI output
- Click for CLI interface
- Pydantic for data validation
- SQLite (built-in)

**Note:** First run will download models (~2GB). Subsequent runs will be much faster.

### 4. Initialize System

```bash
python -m cli.main init
```

This creates necessary directories for data storage.

## 🎯 Running the Demo

### Option 1: Quick Start Script (Fastest)

Process a single review to see all loops in action:

```bash
python quickstart.py
```

**Output shows:**
- Loop 1: Sentiment analysis, issue extraction, response generation
- Loop 2: Multi-criteria verification with scores
- Complete trace with timing

### Option 2: Full Demo (Recommended)

Run the complete demonstration with improvement cycles:

```bash
python -m cli.main demo --reviews 300 --cycles 3
```

**What it does:**
1. **Cycle 0 (Baseline)**: Process 100 reviews, establish baseline metrics
2. **Hill Climbing #1**: Analyze patterns, generate improvement (e.g., enhance tone)
3. **Cycle 1**: Process 100 reviews with improvement, measure impact
4. **Hill Climbing #2**: Find next improvement (e.g., add action steps)
5. **Cycle 2**: Process final 100 reviews, show cumulative improvement

**Expected Results:**
- Baseline pass rate: ~62%
- After 2 cycles: ~75-79%
- Clear improvement in specific criteria (tone, actionability)
- Visual progress bars and metrics

### Option 3: Process Custom Reviews

```bash
# Process 10 reviews
python -m cli.main process --count 10

# Process 50 reviews without retry
python -m cli.main process --count 50 --no-with-retry
```

## 📊 Exploring Results

### View Metrics Dashboard

```bash
python -m cli.main metrics
```

Shows:
- Total reviews processed
- Pass rate and average scores
- Criteria breakdown (relevance, tone, completeness, etc.)
- Common failure patterns

### View Specific Trace

```bash
# First, run some reviews
python -m cli.main process --count 5

# Then view metrics to see trace IDs, or check storage stats
python -m cli.main stats

# Get a trace ID from the database and view it
python -m cli.main trace <trace_id>
```

### Manually Trigger Improvement

```bash
# Analyze last 100 traces and generate improvements
python -m cli.main improve --batch-size 100
```

This runs Loop 4 (Hill Climbing):
1. Analyzes recent traces
2. Detects patterns (low scores, high retries, etc.)
3. Generates improvement hypotheses
4. A/B tests changes
5. Applies successful improvements

## 🔧 Configuration

Edit `.env` file (copy from `.env.example`):

```env
# Model Configuration
SENTIMENT_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest
GENERATION_MODEL=google/flan-t5-base
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Device (cpu, cuda, or mps for Mac M1/M2)
DEVICE=cpu

# Loop Parameters
VERIFICATION_THRESHOLD=0.70
MAX_RETRIES=3
HILL_CLIMBING_BATCH_SIZE=100
HILL_CLIMBING_FREQUENCY=100

# Verification Weights (must sum to 1.0)
WEIGHT_RELEVANCE=0.25
WEIGHT_TONE=0.20
WEIGHT_COMPLETENESS=0.25
WEIGHT_ACTIONABILITY=0.20
WEIGHT_ACCURACY=0.10
```

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 📖 Understanding the Output

### Demo Output Example

```
🔄 Loop Engineering POC Demo
Demonstrating Self-Improving AI Agents with 4 Feedback Loops

✓ Loaded 300 reviews

🎯 Running 3 improvement cycles

======================================================================

Cycle 0: BASELINE
----------------------------------------------------------------------
Processing 100 reviews... ████████████████████ 100% 0:02:15

Pass Rate:      62.0%
Avg Score:      0.67
Avg Retries:    1.2

📋 Criteria Scores:
   • relevance    : 0.75
   • tone         : 0.58  ← LOW
   • completeness : 0.68
   • actionability: 0.60  ← LOW
   • accuracy     : 0.78

🧠 Hill Climbing - Cycle 1
----------------------------------------------------------------------
💡 Hypothesis: Low tone scores for negative sentiment (avg: 0.58)
   Expected: 15.0% improvement
   ✅ Applied: prompt

Cycle 1: AFTER IMPROVEMENT #1
----------------------------------------------------------------------
Processing 100 reviews... ████████████████████ 100% 0:02:10

Pass Rate:      71.0% ↑
Avg Score:      0.73 ↑
Avg Retries:    0.8

📋 Criteria Scores:
   • relevance    : 0.78 ↑
   • tone         : 0.71 ↑ [IMPROVED +24%]
   • completeness : 0.70
   • actionability: 0.62
   • accuracy     : 0.80

[... continues with Cycle 2 ...]

🎉 Demo Complete!

📈 Improvement Summary
======================================================================

🎯 Overall Improvement
Metric          Baseline    Final      Change
Pass Rate       62.0%       79.0%      +17.0%
Avg Score       0.67        0.77       +0.10
Avg Retries     1.20        0.40       -0.80

📊 Criteria Improvements:
  📈 tone        : 0.58 → 0.71 (+0.13)
  📈 actionability: 0.60 → 0.76 (+0.16)
```

## 🎓 What's Happening Under the Hood

### Loop 1: Agent Loop
1. **Sentiment Analysis**: RoBERTa model classifies sentiment
2. **Issue Extraction**: Zero-shot BART model identifies issues
3. **Urgency Classification**: Rule-based priority detection
4. **Knowledge Base Search**: FAISS finds similar successful responses
5. **Response Generation**: T5 model generates contextual response
6. **Trace Logging**: Complete execution record saved to SQLite

### Loop 2: Verification Loop
1. **Multi-Criteria Grading**:
   - Relevance: Does it address the review?
   - Tone: Appropriate empathy/professionalism?
   - Completeness: Covers all issues?
   - Actionability: Clear next steps?
   - Accuracy: No hallucinations?
2. **Score Calculation**: Weighted average (threshold: 0.70)
3. **Retry Logic**: If failed, generate feedback and retry (max 3)
4. **Metrics Tracking**: Store results for hill climbing

### Loop 3: Event-Driven Loop
- Async event queue for orchestration
- Batch processing support
- Triggers hill climbing every 100 reviews
- Coordinates Loop 1 & 2 execution

### Loop 4: Hill Climbing Loop
1. **Pattern Detection**: Analyze 100 recent traces
   - Low criteria scores
   - High retry rates
   - Sentiment-specific issues
2. **Hypothesis Generation**: Propose improvements
   - Update prompts
   - Adjust thresholds
   - Change strategies
3. **A/B Testing**: Test on 40 reviews (20 baseline, 20 treatment)
4. **Apply if Successful**: Automatic improvement if >10% gain

## 🐛 Troubleshooting

### Models won't download
```bash
# Set HuggingFace cache directory
export HF_HOME=/path/to/cache

# Or download models manually
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('google/flan-t5-base')"
```

### Out of memory
```bash
# Use CPU instead of GPU
DEVICE=cpu python -m cli.main demo --reviews 100
```

### Import errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Or create fresh virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### No improvements detected
This is normal! It means the system is performing well. Try:
```bash
# Process more reviews first
python -m cli.main process --count 100

# Then trigger improvement
python -m cli.main improve
```

## 📚 Next Steps

1. **Experiment with Configuration**: Edit `.env` to adjust thresholds and weights
2. **Try Different Datasets**: Modify `dataset_loader.py` to use different review sources
3. **Customize Prompts**: Edit `src/config/prompts.py` to change response style
4. **Add New Criteria**: Extend `response_grader.py` with custom verification criteria
5. **Explore the Code**: Check `src/loops/` to understand each loop's implementation

## 🎯 Key Commands Reference

```bash
# Initialize
python -m cli.main init

# Quick test
python quickstart.py

# Full demo
python -m cli.main demo

# Process reviews
python -m cli.main process --count 10

# View metrics
python -m cli.main metrics

# Trigger improvement
python -m cli.main improve

# View statistics
python -m cli.main stats

# Run tests
pytest tests/ -v
```

## 🏆 Success Criteria

You'll know it's working when you see:
- ✅ Reviews processed through all loops without errors
- ✅ Responses generated that make sense
- ✅ Verification scores calculated (5 criteria)
- ✅ Pass rates improve across cycles (baseline → final)
- ✅ Hill climbing detects patterns and applies improvements

## 💡 Tips

- **First run is slow** (~2-3 min for model downloads) - subsequent runs are fast
- **CPU is fine** for the POC - no GPU needed
- **Start small** - Use `--count 10` first, then scale up
- **Watch the criteria** - Focus on which specific criteria improve
- **A/B tests are simulated** - Uses synthetic reviews for quick demo

## 📞 Need Help?

Check the implementation status:
```bash
cat IMPLEMENTATION_STATUS.md
```

Read the full documentation:
```bash
cat README.md
```

---

**🚀 Ready? Start with:** `python quickstart.py`
