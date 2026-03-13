"""Database access helpers."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Set

import psycopg2
from psycopg2 import pool
from psycopg2.extensions import connection, cursor
from psycopg2.extras import Json, RealDictCursor

from config.settings import settings

from .migrations import run_startup_migrations

logger = logging.getLogger(__name__)

DatabaseUrl = str
DbResult = Optional[Dict[str, Any]]
DbResults = List[Dict[str, Any]]
JsonDict = Dict[str, Any]
if TYPE_CHECKING:
    RealDictCursorType = Any
else:
    RealDictCursorType = RealDictCursor

_db_config: Optional[DatabaseUrl] = None
_connection_pool: Optional[pool.SimpleConnectionPool] = None

# 允许更新的字段白名单（防止SQL注入）
_INTERVIEW_SAFE_UPDATE_FIELDS: Set[str] = {
    "status",
    "completed_at",
    "current_stage",
    "current_message_id",
    "candidate_name",
    "position",
    "skill_domain",
    "skills",
    "experience_level",
    "duration_minutes",
    "additional_requirements",
    "resume_file_id",
    "resume_text",
}


def init_db(
    database_url: DatabaseUrl,
    min_connections: int = 1,
    max_connections: int = 10
) -> None:
    """
    Initialize DB config, connection pool and ensure startup migrations are applied.

    Args:
        database_url: PostgreSQL connection URL
        min_connections: Minimum number of connections in the pool
        max_connections: Maximum number of connections in the pool
    """
    global _db_config, _connection_pool
    _db_config = database_url

    # 创建连接池
    try:
        _connection_pool = pool.SimpleConnectionPool(
            min_connections,
            max_connections,
            database_url
        )
        logger.info(
            f"Database connection pool initialized: "
            f"{min_connections}-{max_connections} connections"
        )
    except Exception as e:
        logger.error(f"Failed to create connection pool: {e}")
        raise

    # 运行迁移
    run_startup_migrations(database_url)


def get_connection() -> connection:
    """
    Get a database connection from the pool.

    Returns:
        Database connection

    Raises:
        RuntimeError: If database is not initialized or pool is exhausted
    """
    if _connection_pool is None:
        raise RuntimeError("Database connection pool is not initialized. Call init_db() first.")

    try:
        conn = _connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        raise RuntimeError(f"Failed to acquire database connection: {e}")


def release_connection(conn: connection) -> None:
    """
    Release a connection back to the pool.

    Args:
        conn: Database connection to release
    """
    if _connection_pool is not None:
        _connection_pool.putconn(conn)


def close_all_connections() -> None:
    """Close all connections in the pool. Call this when shutting down the application."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("All database connections closed")


@contextmanager
def get_db_cursor() -> Generator[cursor, None, None]:
    """
    Yield a transactional cursor from a pooled connection.

    The connection is automatically returned to the pool after the context manager exits.

    Yields:
        Database cursor with RealDictCursor factory

    Example:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM interviews")
            results = cur.fetchall()
    """
    if _connection_pool is None:
        raise RuntimeError("Database connection pool is not initialized. Call init_db() first.")

    conn: Optional[connection] = None
    cur: Optional[cursor] = None

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursorType)
        yield cur
        conn.commit()
    except Exception:
        if conn is not None:
            conn.rollback()
        logger.exception("Database operation failed")
        raise
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            release_connection(conn)


# Interview operations

def create_interview(interview_data: Dict[str, Any]) -> int:
    """Create one interview."""
    sql = """
    INSERT INTO interviews (
        candidate_name,
        position,
        skill_domain,
        skills,
        experience_level,
        duration_minutes,
        additional_requirements,
        resume_file_id,
        resume_text,
        status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(
            sql,
            (
                interview_data["candidate_name"],
                interview_data["position"],
                interview_data["skill_domain"],
                interview_data["skills"],
                interview_data.get("experience_level", "mid"),
                interview_data.get("duration_minutes", 30),
                interview_data.get("additional_requirements"),
                interview_data.get("resume_file_id"),
                interview_data.get("resume_text"),
                "created",
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to create interview")
        return result["id"]


def get_interview(interview_id: int) -> DbResult:
    """Get one interview and whether an expression report exists."""
    sql = """
    SELECT
        interviews.*,
        EXISTS (
            SELECT 1
            FROM expression_analysis_reports
            WHERE expression_analysis_reports.interview_id = interviews.id
        ) AS expression_report_ready
    FROM interviews
    WHERE interviews.id = %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchone()


def list_interviews(limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[dict]:
    """List interviews with optional status filter."""
    sql = """
    SELECT
        interviews.*,
        EXISTS (
            SELECT 1
            FROM expression_analysis_reports
            WHERE expression_analysis_reports.interview_id = interviews.id
        ) AS expression_report_ready
    FROM interviews
    """
    params: List[Any] = []

    if status:
        sql += " WHERE status = %s"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def update_interview_status(interview_id: int, status: str) -> bool:
    """
    Update interview status.

    Args:
        interview_id: Interview ID
        status: New status (e.g., 'created', 'in_progress', 'completed')

    Returns:
        True if update was successful, False otherwise
    """
    update_fields = ["status = %s"]
    params: List[Any] = [status]

    if status == "completed":
        update_fields.append("completed_at = CURRENT_TIMESTAMP")

    params.append(interview_id)

    # 使用白名单验证字段名，防止SQL注入
    # 虽然这里的 update_fields 是内部定义的，但为了安全起见，我们仍然验证
    safe_fields = []
    for field in update_fields:
        # 提取字段名（去掉 " = %s" 部分）
        field_name = field.split()[0]
        if field_name in _INTERVIEW_SAFE_UPDATE_FIELDS or field_name in {
            "updated_at",  # 自动更新的时间戳字段
            "completed_at"  # 完成时间戳字段
        }:
            safe_fields.append(field)
        else:
            logger.warning(f"Attempted to update unsafe field: {field_name}")
            raise ValueError(f"Cannot update field: {field_name}")

    sql = f"UPDATE interviews SET {', '.join(safe_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount > 0


def delete_interview(interview_id: int) -> bool:
    """Delete one interview."""
    sql = "DELETE FROM interviews WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.rowcount > 0


def update_interview_stage(interview_id: int, current_stage: str) -> bool:
    """Update the current interview stage."""
    sql = "UPDATE interviews SET current_stage = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (current_stage, interview_id))
        return cur.rowcount > 0


def update_interview_current_message(interview_id: int, current_message_id: int) -> bool:
    """Update the current message pointer for an interview."""
    sql = "UPDATE interviews SET current_message_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (current_message_id, interview_id))
        return cur.rowcount > 0


def get_interview_current_message(interview_id: int) -> Optional[int]:
    """Get the current message id for an interview."""
    sql = "SELECT current_message_id FROM interviews WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        result = cur.fetchone()
        return result["current_message_id"] if result else None


# Message operations

def create_message(
    interview_id: int,
    role: str,
    content: str,
    parent_id: Optional[int] = None,
    branch_id: str = "main",
) -> int:
    """Create one message with tree metadata."""
    if parent_id is None:
        sql = """
        SELECT id FROM messages
        WHERE interview_id = %s AND branch_id = %s AND is_active = true
        ORDER BY timestamp DESC
        LIMIT 1
        """
        with get_db_cursor() as cur:
            cur.execute(sql, (interview_id, branch_id))
            result = cur.fetchone()
            if result:
                parent_id = result["id"]

    tree_path: List[int] = []
    if parent_id:
        sql = "SELECT tree_path FROM messages WHERE id = %s"
        with get_db_cursor() as cur:
            cur.execute(sql, (parent_id,))
            result = cur.fetchone()
            if result and result["tree_path"]:
                tree_path = list(result["tree_path"])
            tree_path.append(parent_id)

    sql = """
    INSERT INTO messages (interview_id, role, content, parent_id, branch_id, tree_path)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, role, content, parent_id, branch_id, tree_path))
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to create message")
        return result["id"]


def update_message_content(message_id: int, content: str) -> bool:
    """Update message content after a streaming response completes."""
    sql = """
    UPDATE messages
    SET content = %s, timestamp = CURRENT_TIMESTAMP
    WHERE id = %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (content, message_id))
        return cur.rowcount > 0


def get_messages(interview_id: int, limit: int = 100) -> List[dict]:
    """List messages for one interview."""
    sql = """
    SELECT
        id,
        interview_id,
        role,
        content,
        timestamp,
        parent_id,
        branch_id,
        tree_path,
        is_active
    FROM messages
    WHERE interview_id = %s
    ORDER BY timestamp ASC
    LIMIT %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, limit))
        return cur.fetchall()


def get_message_path(interview_id: int, message_id: int) -> List[dict]:
    """Get the message path from root to the current node."""
    sql = """
    WITH RECURSIVE message_path AS (
        SELECT
            id,
            interview_id,
            role,
            content,
            timestamp,
            parent_id,
            branch_id,
            tree_path,
            is_active
        FROM messages
        WHERE id = %s AND interview_id = %s

        UNION ALL

        SELECT
            m.id,
            m.interview_id,
            m.role,
            m.content,
            m.timestamp,
            m.parent_id,
            m.branch_id,
            m.tree_path,
            m.is_active
        FROM messages m
        INNER JOIN message_path mp ON mp.parent_id = m.id
        WHERE m.interview_id = %s
    )
    SELECT
        id,
        interview_id,
        role,
        content,
        timestamp,
        parent_id,
        branch_id,
        tree_path,
        is_active
    FROM message_path
    ORDER BY timestamp ASC, id ASC
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (message_id, interview_id, interview_id))
        return cur.fetchall()


def delete_messages(interview_id: int) -> bool:
    """Delete all messages for one interview."""
    sql = "DELETE FROM messages WHERE interview_id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.rowcount > 0


# Snapshot operations

def create_snapshot(snapshot_data: dict) -> int:
    """Create one interview snapshot."""
    sql = """
    INSERT INTO interview_snapshots (interview_id, name, description, snapshot_data)
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(
            sql,
            (
                snapshot_data["interview_id"],
                snapshot_data["name"],
                snapshot_data.get("description", ""),
                json.dumps(snapshot_data["snapshot_data"], ensure_ascii=False),
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to create snapshot")
        return result["id"]


def get_snapshots(interview_id: int) -> List[dict]:
    """List snapshots for one interview."""
    sql = """
    SELECT *
    FROM interview_snapshots
    WHERE interview_id = %s
    ORDER BY created_at DESC
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchall()


def get_snapshot(snapshot_id: int) -> Optional[dict]:
    """Get one snapshot."""
    sql = "SELECT * FROM interview_snapshots WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (snapshot_id,))
        return cur.fetchone()


def delete_snapshot(snapshot_id: int) -> bool:
    """Delete one snapshot."""
    sql = "DELETE FROM interview_snapshots WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (snapshot_id,))
        return cur.rowcount > 0


def load_snapshot(snapshot_id: int) -> Optional[dict]:
    """Load decoded snapshot payload."""
    snapshot = get_snapshot(snapshot_id)
    if not snapshot:
        return None

    snapshot_data = snapshot["snapshot_data"]
    if isinstance(snapshot_data, dict):
        return snapshot_data
    if isinstance(snapshot_data, str):
        return json.loads(snapshot_data)
    return None


# Tool orchestration operations

def create_tool_invocation(invocation_data: dict) -> int:
    """Persist one external tool invocation record."""
    sql = """
    INSERT INTO tool_invocations (
        trace_id, interview_id, stage, trigger, tool_name,
        request_payload, response_payload, status, latency_ms, cache_hit
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(
            sql,
            (
                invocation_data.get("trace_id"),
                invocation_data["interview_id"],
                invocation_data["stage"],
                invocation_data["trigger"],
                invocation_data["tool_name"],
                Json(invocation_data.get("request_payload") or {}, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                Json(invocation_data.get("response_payload") or {}, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                invocation_data.get("status", "success"),
                int(invocation_data.get("latency_ms") or 0),
                bool(invocation_data.get("cache_hit", False)),
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to create tool invocation")
        return result["id"]


def list_tool_invocations(interview_id: int, limit: int = 100) -> List[dict]:
    """List tool invocations for one interview."""
    sql = """
    SELECT *
    FROM tool_invocations
    WHERE interview_id = %s
    ORDER BY created_at DESC, id DESC
    LIMIT %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, limit))
        return cur.fetchall()


def upsert_interview_tool_context(context_data: dict) -> int:
    """Insert or update reusable tool context cache."""
    update_sql = """
    UPDATE interview_tool_contexts
    SET prompt_context = %s,
        structured_payload = %s,
        expires_at = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE interview_id = %s AND stage = %s AND tool_name = %s AND context_key = %s
    RETURNING id
    """
    insert_sql = """
    INSERT INTO interview_tool_contexts (
        interview_id, stage, tool_name, context_key, prompt_context, structured_payload, expires_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    structured_payload = context_data.get("structured_payload") or {}
    with get_db_cursor() as cur:
        cur.execute(
            update_sql,
            (
                context_data.get("prompt_context", ""),
                Json(structured_payload, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                context_data.get("expires_at"),
                context_data["interview_id"],
                context_data["stage"],
                context_data["tool_name"],
                context_data["context_key"],
            ),
        )
        result = cur.fetchone()
        if result:
            return result["id"]

        cur.execute(
            insert_sql,
            (
                context_data["interview_id"],
                context_data["stage"],
                context_data["tool_name"],
                context_data["context_key"],
                context_data.get("prompt_context", ""),
                Json(structured_payload, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                context_data.get("expires_at"),
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to upsert tool context")
        return result["id"]


def get_interview_tool_context(
    interview_id: int,
    stage: str,
    tool_name: str,
    context_key: str,
) -> Optional[dict]:
    """Get one active tool context cache row."""
    sql = """
    SELECT *
    FROM interview_tool_contexts
    WHERE interview_id = %s
      AND stage = %s
      AND tool_name = %s
      AND context_key = %s
      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
    ORDER BY updated_at DESC, id DESC
    LIMIT 1
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, stage, tool_name, context_key))
        return cur.fetchone()


def list_interview_tool_contexts(interview_id: int, include_expired: bool = False) -> List[dict]:
    """List reusable tool contexts for one interview."""
    sql = """
    SELECT *
    FROM interview_tool_contexts
    WHERE interview_id = %s
    """
    params: List[Any] = [interview_id]
    if not include_expired:
        sql += " AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)"
    sql += " ORDER BY updated_at DESC, id DESC"

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


# Expression analysis operations

def upsert_expression_feature_segment(feature_data: dict) -> int:
    """Insert or update one expression feature segment/window."""
    update_sql = """
    UPDATE expression_feature_segments
    SET stage = %s,
        source = %s,
        started_at = %s,
        ended_at = %s,
        metrics = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE interview_id = %s AND feature_type = %s AND segment_key = %s
    RETURNING id
    """
    insert_sql = """
    INSERT INTO expression_feature_segments (
        interview_id, feature_type, segment_key, stage, source, started_at, ended_at, metrics
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    metrics = feature_data.get("metrics") or {}
    with get_db_cursor() as cur:
        cur.execute(
            update_sql,
            (
                feature_data.get("stage"),
                feature_data.get("source"),
                feature_data.get("started_at"),
                feature_data.get("ended_at"),
                Json(metrics, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                feature_data["interview_id"],
                feature_data["feature_type"],
                feature_data["segment_key"],
            ),
        )
        result = cur.fetchone()
        if result:
            return result["id"]

        cur.execute(
            insert_sql,
            (
                feature_data["interview_id"],
                feature_data["feature_type"],
                feature_data["segment_key"],
                feature_data.get("stage"),
                feature_data.get("source"),
                feature_data.get("started_at"),
                feature_data.get("ended_at"),
                Json(metrics, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to upsert expression feature segment")
        return result["id"]


def list_expression_feature_segments(interview_id: int, feature_type: Optional[str] = None) -> List[dict]:
    """List expression feature rows for one interview."""
    sql = """
    SELECT *
    FROM expression_feature_segments
    WHERE interview_id = %s
    """
    params: List[Any] = [interview_id]
    if feature_type:
        sql += " AND feature_type = %s"
        params.append(feature_type)
    sql += " ORDER BY COALESCE(ended_at, started_at, created_at) ASC, id ASC"

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def save_expression_analysis_report(report_data: dict) -> int:
    """Replace the latest expression analysis report for one interview."""
    delete_sql = "DELETE FROM expression_analysis_reports WHERE interview_id = %s"
    insert_sql = """
    INSERT INTO expression_analysis_reports (
        interview_id, overall_score, confidence_level, confidence_score,
        modality_coverage, metrics, dimension_scores, evidence_summary,
        risk_flags, narrative_summary
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(delete_sql, (report_data["interview_id"],))
        cur.execute(
            insert_sql,
            (
                report_data["interview_id"],
                report_data["overall_score"],
                report_data["confidence_level"],
                report_data["confidence_score"],
                Json(report_data.get("modality_coverage") or {}, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                Json(report_data.get("metrics") or {}, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                Json(report_data.get("dimension_scores") or {}, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                Json(report_data.get("evidence_summary") or [], dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                Json(report_data.get("risk_flags") or [], dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                report_data.get("narrative_summary") or "",
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to save expression analysis report")
        return result["id"]


def get_expression_analysis_report(interview_id: int) -> Optional[dict]:
    """Get the latest expression analysis report for one interview."""
    sql = """
    SELECT *
    FROM expression_analysis_reports
    WHERE interview_id = %s
    ORDER BY updated_at DESC, id DESC
    LIMIT 1
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchone()


# Prompt config operations

def save_prompt_config(config_data: dict, config_type: str = "default") -> int:
    """Upsert one prompt config payload."""
    sql = """
    INSERT INTO prompt_configs (config_type, config_data, updated_at)
    VALUES (%s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (config_type) DO UPDATE SET
        config_data = EXCLUDED.config_data,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (config_type, json.dumps(config_data, ensure_ascii=False)))
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to save prompt config")
        return result["id"]


def get_prompt_config(config_type: str = "default") -> Optional[dict]:
    """Get one prompt config payload."""
    sql = "SELECT config_data FROM prompt_configs WHERE config_type = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (config_type,))
        result = cur.fetchone()
        if not result:
            return None

        config_data = result["config_data"]
        if isinstance(config_data, dict):
            return config_data
        if isinstance(config_data, str):
            return json.loads(config_data)
        return None


# Profile plugin operations

def create_profile_plugin(plugin_data: dict) -> int:
    """Create one profile plugin."""
    sql = """
    INSERT INTO profile_plugins (plugin_id, type, name, description, is_system, config)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(
            sql,
            (
                plugin_data["plugin_id"],
                plugin_data["type"],
                plugin_data["name"],
                plugin_data.get("description", ""),
                plugin_data.get("is_system", False),
                json.dumps(plugin_data.get("config", {}), ensure_ascii=False),
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to create profile plugin")
        return result["id"]


def get_profile_plugin(plugin_id: str) -> Optional[dict]:
    """Get one profile plugin."""
    sql = "SELECT * FROM profile_plugins WHERE plugin_id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (plugin_id,))
        return cur.fetchone()


def list_profile_plugins(plugin_type: Optional[str] = None, is_system: Optional[bool] = None) -> List[dict]:
    """List profile plugins."""
    sql = "SELECT * FROM profile_plugins WHERE 1=1"
    params: List[Any] = []

    if plugin_type:
        sql += " AND type = %s"
        params.append(plugin_type)

    if is_system is not None:
        sql += " AND is_system = %s"
        params.append(is_system)

    sql += " ORDER BY created_at DESC"
    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def update_profile_plugin(plugin_id: str, plugin_data: dict) -> bool:
    """Update one profile plugin."""
    sql = """
    UPDATE profile_plugins
    SET name = %s, description = %s, config = %s, updated_at = CURRENT_TIMESTAMP
    WHERE plugin_id = %s
    """
    with get_db_cursor() as cur:
        cur.execute(
            sql,
            (
                plugin_data["name"],
                plugin_data.get("description", ""),
                json.dumps(plugin_data.get("config", {}), ensure_ascii=False),
                plugin_id,
            ),
        )
        return cur.rowcount > 0


def delete_profile_plugin(plugin_id: str) -> bool:
    """Delete one non-system profile plugin."""
    sql = "DELETE FROM profile_plugins WHERE plugin_id = %s AND is_system = FALSE"
    with get_db_cursor() as cur:
        cur.execute(sql, (plugin_id,))
        return cur.rowcount > 0


def apply_interview_profile(
    interview_id: int,
    position_plugin_id: str,
    interviewer_plugin_id: str,
    custom_config: Optional[dict] = None,
) -> int:
    """Apply profile config to an interview."""
    update_sql = """
    UPDATE interview_profiles
    SET position_plugin_id = %s,
        interviewer_plugin_id = %s,
        custom_config = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE interview_id = %s
    RETURNING id
    """
    insert_sql = """
    INSERT INTO interview_profiles (interview_id, position_plugin_id, interviewer_plugin_id, custom_config)
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """
    custom_config_json = json.dumps(custom_config or {}, ensure_ascii=False)

    with get_db_cursor() as cur:
        cur.execute(
            update_sql,
            (
                position_plugin_id,
                interviewer_plugin_id,
                custom_config_json,
                interview_id,
            ),
        )
        result = cur.fetchone()
        if result:
            return result["id"]

        cur.execute(
            insert_sql,
            (
                interview_id,
                position_plugin_id,
                interviewer_plugin_id,
                custom_config_json,
            ),
        )
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Failed to apply interview profile")
        return result["id"]


def get_interview_profile(interview_id: int) -> Optional[dict]:
    """Get profile binding for one interview."""
    sql = """
    SELECT
        ip.*,
        pp1.name as position_name,
        pp1.description as position_description,
        pp1.config as position_config,
        pp2.name as interviewer_name,
        pp2.description as interviewer_description,
        pp2.config as interviewer_config
    FROM interview_profiles ip
    LEFT JOIN profile_plugins pp1 ON ip.position_plugin_id = pp1.plugin_id
    LEFT JOIN profile_plugins pp2 ON ip.interviewer_plugin_id = pp2.plugin_id
    WHERE ip.interview_id = %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchone()


def init_default_profiles() -> None:
    """Upsert built-in profile presets."""
    default_profiles = [
        {
            "plugin_id": "position_frontend_junior",
            "type": "position",
            "name": "Junior Frontend Engineer",
            "description": "Suitable for 1-3 years of frontend experience.",
            "is_system": True,
            "config": {
                "ability_weights": {
                    "technical": 0.6,
                    "communication": 0.15,
                    "problem_solving": 0.15,
                    "learning_potential": 0.1,
                },
                "skill_requirements": {
                    "core_skills": ["HTML/CSS", "JavaScript", "Vue.js/React"],
                    "weights": {"HTML/CSS": 0.3, "JavaScript": 0.4, "Vue.js/React": 0.3},
                },
            },
        },
        {
            "plugin_id": "position_frontend_mid",
            "type": "position",
            "name": "Mid-level Frontend Engineer",
            "description": "Suitable for 3-5 years of frontend experience.",
            "is_system": True,
            "config": {
                "ability_weights": {
                    "technical": 0.5,
                    "communication": 0.2,
                    "problem_solving": 0.2,
                    "learning_potential": 0.1,
                },
                "skill_requirements": {
                    "core_skills": ["Vue.js", "TypeScript", "Engineering"],
                    "weights": {"Vue.js": 0.35, "TypeScript": 0.35, "Engineering": 0.3},
                },
            },
        },
        {
            "plugin_id": "position_backend_senior",
            "type": "position",
            "name": "Senior Backend Engineer",
            "description": "Suitable for 5+ years of backend experience.",
            "is_system": True,
            "config": {
                "ability_weights": {
                    "technical": 0.4,
                    "communication": 0.2,
                    "problem_solving": 0.25,
                    "learning_potential": 0.15,
                },
                "skill_requirements": {
                    "core_skills": ["Architecture", "Performance", "System Design"],
                    "weights": {"Architecture": 0.4, "Performance": 0.3, "System Design": 0.3},
                },
            },
        },
    ]
    default_profiles.extend(settings.interviewer_profile_presets)

    for profile in default_profiles:
        try:
            existing = get_profile_plugin(profile["plugin_id"])
            if existing:
                update_profile_plugin(
                    profile["plugin_id"],
                    {
                        "name": profile["name"],
                        "description": profile.get("description", ""),
                        "config": profile.get("config", {}),
                    },
                )
            else:
                create_profile_plugin(profile)
        except Exception as e:
            logger.warning("Failed to upsert default profile %s: %s", profile.get("plugin_id"), e)

    logger.info("Default profiles initialized")
