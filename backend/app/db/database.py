"""
数据库操作模块
"""
import psycopg2
from psycopg2.extras import RealDictCursor, DictCursor
from typing import Optional, List, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


# 数据库连接池（简化版）
_db_config = None


def init_db(database_url: str):
    """初始化数据库配置"""
    global _db_config
    _db_config = database_url
    _create_tables()


def get_connection():
    """获取数据库连接"""
    if _db_config is None:
        raise RuntimeError("数据库未初始化")
    return psycopg2.connect(_db_config)


@contextmanager
def get_db_cursor():
    """获取数据库游标上下文管理器"""
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库操作错误: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def _create_tables():
    """创建数据库表"""
    create_interviews_table = """
    CREATE TABLE IF NOT EXISTS interviews (
        id SERIAL PRIMARY KEY,
        candidate_name VARCHAR(255) NOT NULL,
        position VARCHAR(255) NOT NULL,
        skill_domain VARCHAR(50) NOT NULL,
        skills TEXT[] NOT NULL,
        experience_level VARCHAR(50) DEFAULT '中级',
        duration_minutes INTEGER DEFAULT 30,
        additional_requirements TEXT,
        status VARCHAR(50) DEFAULT 'created',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        completed_at TIMESTAMP
    );
    """

    create_messages_table = """
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_evaluations_table = """
    CREATE TABLE IF NOT EXISTS evaluations (
        id SERIAL PRIMARY KEY,
        interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
        overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
        dimension_scores JSONB,
        strengths TEXT[],
        weaknesses TEXT[],
        recommendation VARCHAR(50),
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # 创建索引
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_messages_interview_id ON messages(interview_id);",
        "CREATE INDEX IF NOT EXISTS idx_evaluations_interview_id ON evaluations(interview_id);",
        "CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);",
    ]

    try:
        with get_db_cursor() as cur:
            cur.execute(create_interviews_table)
            cur.execute(create_messages_table)
            cur.execute(create_evaluations_table)
            for index_sql in create_indexes:
                cur.execute(index_sql)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise


# ==================== 面试相关操作 ====================

def create_interview(interview_data: dict) -> int:
    """创建面试"""
    sql = """
    INSERT INTO interviews (candidate_name, position, skill_domain, skills,
                           experience_level, duration_minutes, additional_requirements, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (
            interview_data['candidate_name'],
            interview_data['position'],
            interview_data['skill_domain'],
            interview_data['skills'],
            interview_data.get('experience_level', '中级'),
            interview_data.get('duration_minutes', 30),
            interview_data.get('additional_requirements'),
            'created'
        ))
        result = cur.fetchone()
        return result['id']


def get_interview(interview_id: int) -> Optional[dict]:
    """获取面试详情"""
    sql = "SELECT * FROM interviews WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchone()


def list_interviews(limit: int = 50, offset: int = 0, status: str = None) -> List[dict]:
    """列出面试"""
    sql = "SELECT * FROM interviews"
    params = []

    if status:
        sql += " WHERE status = %s"
        params.append(status)

    sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def update_interview_status(interview_id: int, status: str) -> bool:
    """更新面试状态"""
    update_fields = ["status = %s"]
    params = [status]

    if status == "completed":
        update_fields.append("completed_at = CURRENT_TIMESTAMP")

    params.append(interview_id)
    sql = f"UPDATE interviews SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"

    with get_db_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount > 0


def delete_interview(interview_id: int) -> bool:
    """删除面试"""
    sql = "DELETE FROM interviews WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.rowcount > 0


# ==================== 消息相关操作 ====================

def create_message(interview_id: int, role: str, content: str) -> int:
    """创建消息"""
    sql = """
    INSERT INTO messages (interview_id, role, content)
    VALUES (%s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, role, content))
        result = cur.fetchone()
        return result['id']


def get_messages(interview_id: int, limit: int = 100) -> List[dict]:
    """获取面试消息"""
    sql = """
    SELECT * FROM messages
    WHERE interview_id = %s
    ORDER BY timestamp ASC
    LIMIT %s
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, limit))
        return cur.fetchall()


def delete_messages(interview_id: int) -> bool:
    """删除面试的所有消息"""
    sql = "DELETE FROM messages WHERE interview_id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.rowcount > 0


# ==================== 评估相关操作 ====================

def create_evaluation(evaluation_data: dict) -> int:
    """创建评估"""
    sql = """
    INSERT INTO evaluations (interview_id, overall_score, dimension_scores,
                            strengths, weaknesses, recommendation, feedback)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (
            evaluation_data['interview_id'],
            evaluation_data['overall_score'],
            evaluation_data['dimension_scores'],
            evaluation_data['strengths'],
            evaluation_data['weaknesses'],
            evaluation_data['recommendation'],
            evaluation_data['feedback']
        ))
        result = cur.fetchone()
        return result['id']


def get_evaluation(interview_id: int) -> Optional[dict]:
    """获取面试评估"""
    sql = "SELECT * FROM evaluations WHERE interview_id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchone()
