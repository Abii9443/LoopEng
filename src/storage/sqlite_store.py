"""SQLite storage for traces, metrics, and improvements."""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from src.config import settings
from src.models.trace import ExecutionTrace
from src.models.metrics import SystemMetrics
from src.models.improvement import ImprovementHypothesis, ABTestResult

logger = structlog.get_logger()


class SQLiteStore:
    """SQLite database for persistent storage."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or settings.database_path
        self.conn = None
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, initializing if needed."""
        if not self._initialized:
            self._initialize()
        return self.conn

    def _initialize(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            return

        # Ensure directory exists
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Initializing SQLite database", path=self.db_path)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._create_tables()
        self._initialized = True

        logger.info("SQLite database initialized")

    def _create_tables(self):
        """Create database tables."""
        cursor = self.conn.cursor()

        # Traces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                review_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                steps_json TEXT NOT NULL,
                tools_used_json TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                response_json TEXT NOT NULL,
                verification_json TEXT,
                prompt_version TEXT NOT NULL,
                model_config_json TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                window_start DATETIME NOT NULL,
                window_end DATETIME NOT NULL,
                total_reviews_processed INTEGER NOT NULL,
                avg_response_time_ms REAL NOT NULL,
                verification_pass_rate REAL NOT NULL,
                avg_verification_score REAL NOT NULL,
                criteria_breakdown_json TEXT NOT NULL,
                improvement_cycles INTEGER DEFAULT 0,
                score_trend_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Improvements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvements (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                pattern TEXT NOT NULL,
                supporting_traces_json TEXT NOT NULL,
                change_type TEXT NOT NULL,
                current_value TEXT NOT NULL,
                proposed_value TEXT NOT NULL,
                expected_improvement REAL NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                actual_improvement REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AB test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                baseline_traces_json TEXT NOT NULL,
                treatment_traces_json TEXT NOT NULL,
                baseline_score REAL NOT NULL,
                treatment_score REAL NOT NULL,
                improvement REAL NOT NULL,
                relative_improvement REAL NOT NULL,
                is_significant BOOLEAN NOT NULL,
                should_apply BOOLEAN NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hypothesis_id) REFERENCES improvements(id)
            )
        """)

        # Create indices for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_traces_success ON traces(success)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_traces_review_id ON traces(review_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_improvements_status ON improvements(status)")

        self.conn.commit()

    def save_trace(self, trace: ExecutionTrace):
        """Save execution trace to database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO traces (
                id, review_id, timestamp, steps_json, tools_used_json,
                duration_ms, response_json, verification_json,
                prompt_version, model_config_json, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace.id,
            trace.review_id,
            trace.timestamp.isoformat(),
            json.dumps([step.model_dump() for step in trace.steps]),
            json.dumps(trace.tools_used),
            trace.duration_ms,
            json.dumps(trace.response.model_dump()),
            json.dumps(trace.verification.model_dump()) if trace.verification else None,
            trace.prompt_version,
            json.dumps(trace.model_config),
            trace.success
        ))

        conn.commit()
        logger.debug("Trace saved", trace_id=trace.id)

    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Get trace by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM traces WHERE id = ?", (trace_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_trace(row)

    def get_recent_traces(self, limit: int = 100, success_only: bool = False) -> List[ExecutionTrace]:
        """Get recent traces."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM traces"
        if success_only:
            query += " WHERE success = 1"
        query += " ORDER BY timestamp DESC LIMIT ?"

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        return [self._row_to_trace(row) for row in rows]

    def _row_to_trace(self, row: sqlite3.Row) -> ExecutionTrace:
        """Convert database row to ExecutionTrace."""
        from src.models.trace import AgentStep, ToolCall
        from src.models.response import Response
        from src.models.verification import VerificationResult, CriteriaScore

        # Parse JSON fields
        steps_data = json.loads(row['steps_json'])
        steps = [AgentStep(**step_data) for step_data in steps_data]

        response = Response(**json.loads(row['response_json']))

        verification = None
        if row['verification_json']:
            verification_data = json.loads(row['verification_json'])
            # Reconstruct criteria_scores
            criteria_scores = {}
            for key, value in verification_data['criteria_scores'].items():
                criteria_scores[key] = CriteriaScore(**value)
            verification_data['criteria_scores'] = criteria_scores
            verification = VerificationResult(**verification_data)

        return ExecutionTrace(
            id=row['id'],
            review_id=row['review_id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            steps=steps,
            tools_used=json.loads(row['tools_used_json']),
            duration_ms=row['duration_ms'],
            response=response,
            verification=verification,
            prompt_version=row['prompt_version'],
            model_config=json.loads(row['model_config_json']),
            success=bool(row['success'])
        )

    def save_metrics(self, metrics: SystemMetrics):
        """Save system metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO metrics (
                timestamp, window_start, window_end,
                total_reviews_processed, avg_response_time_ms,
                verification_pass_rate, avg_verification_score,
                criteria_breakdown_json, improvement_cycles, score_trend_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.timestamp.isoformat(),
            metrics.window_start.isoformat(),
            metrics.window_end.isoformat(),
            metrics.total_reviews_processed,
            metrics.avg_response_time_ms,
            metrics.verification_pass_rate,
            metrics.avg_verification_score,
            json.dumps(metrics.criteria_breakdown),
            metrics.improvement_cycles,
            json.dumps(metrics.score_trend)
        ))

        conn.commit()
        logger.debug("Metrics saved")

    def save_improvement(self, hypothesis: ImprovementHypothesis):
        """Save improvement hypothesis."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO improvements (
                id, timestamp, pattern, supporting_traces_json,
                change_type, current_value, proposed_value,
                expected_improvement, confidence, status, actual_improvement
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hypothesis.id,
            hypothesis.timestamp.isoformat(),
            hypothesis.pattern,
            json.dumps(hypothesis.supporting_traces),
            hypothesis.change_type,
            hypothesis.current_value,
            hypothesis.proposed_value,
            hypothesis.expected_improvement,
            hypothesis.confidence,
            hypothesis.status,
            hypothesis.actual_improvement
        ))

        conn.commit()
        logger.debug("Improvement hypothesis saved", hypothesis_id=hypothesis.id)

    def update_improvement_status(
        self,
        hypothesis_id: str,
        status: str,
        actual_improvement: Optional[float] = None
    ):
        """Update improvement hypothesis status."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE improvements
            SET status = ?, actual_improvement = ?
            WHERE id = ?
        """, (status, actual_improvement, hypothesis_id))

        conn.commit()

    def save_ab_test_result(self, result: ABTestResult):
        """Save A/B test result."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ab_test_results (
                hypothesis_id, timestamp,
                baseline_traces_json, treatment_traces_json,
                baseline_score, treatment_score,
                improvement, relative_improvement,
                is_significant, should_apply
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.hypothesis_id,
            result.timestamp.isoformat(),
            json.dumps(result.baseline_traces),
            json.dumps(result.treatment_traces),
            result.baseline_score,
            result.treatment_score,
            result.improvement,
            result.relative_improvement,
            result.is_significant,
            result.should_apply
        ))

        conn.commit()
        logger.debug("A/B test result saved", hypothesis_id=result.hypothesis_id)

    def get_count(self, table: str = "traces") -> int:
        """Get count of records in a table."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        return cursor.fetchone()[0]

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self._initialized = False
            logger.info("SQLite connection closed")
