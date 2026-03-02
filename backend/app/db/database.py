"""
数据库操作模块
"""
import psycopg2
from psycopg2.extras import RealDictCursor, DictCursor, Json
from typing import Optional, List, Any
from contextlib import contextmanager
import logging
import json

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
        resume_file_id VARCHAR(255),
        resume_text TEXT,
        status VARCHAR(50) DEFAULT 'created',
        current_stage VARCHAR(50) DEFAULT 'welcome',
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
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parent_id INTEGER REFERENCES messages(id) ON DELETE CASCADE,
        branch_id VARCHAR(100) DEFAULT 'main',
        tree_path TEXT[] DEFAULT '{}',
        is_active BOOLEAN DEFAULT true
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
        recommendation TEXT,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_prompt_configs_table = """
    CREATE TABLE IF NOT EXISTS prompt_configs (
        id SERIAL PRIMARY KEY,
        config_type VARCHAR(50) UNIQUE NOT NULL,
        config_data JSONB NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_interview_snapshots_table = """
    CREATE TABLE IF NOT EXISTS interview_snapshots (
        id SERIAL PRIMARY KEY,
        interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        snapshot_data JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_profile_plugins_table = """
    CREATE TABLE IF NOT EXISTS profile_plugins (
        id SERIAL PRIMARY KEY,
        plugin_id VARCHAR(50) UNIQUE NOT NULL,
        type VARCHAR(20) NOT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        is_system BOOLEAN DEFAULT FALSE,
        config JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    create_interview_profiles_table = """
    CREATE TABLE IF NOT EXISTS interview_profiles (
        id SERIAL PRIMARY KEY,
        interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
        position_plugin_id VARCHAR(50),
        interviewer_plugin_id VARCHAR(50),
        custom_config JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(interview_id)
    );
    """

    # 创建索引
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_messages_interview_id ON messages(interview_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_parent_id ON messages(parent_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_branch_id ON messages(branch_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_is_active ON messages(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_evaluations_interview_id ON evaluations(interview_id);",
        "CREATE INDEX IF NOT EXISTS idx_interviews_status ON interviews(status);",
        "CREATE INDEX IF NOT EXISTS idx_interviews_current_stage ON interviews(current_stage);",
        "CREATE INDEX IF NOT EXISTS idx_snapshots_interview_id ON interview_snapshots(interview_id);",
        "CREATE INDEX IF NOT EXISTS idx_profile_plugins_type ON profile_plugins(type);",
        "CREATE INDEX IF NOT EXISTS idx_profile_plugins_plugin_id ON profile_plugins(plugin_id);",
        "CREATE INDEX IF NOT EXISTS idx_interview_profiles_interview_id ON interview_profiles(interview_id);",
    ]

    try:
        with get_db_cursor() as cur:
            # 创建所有表
            cur.execute(create_interviews_table)
            cur.execute(create_messages_table)
            cur.execute(create_evaluations_table)
            cur.execute(create_prompt_configs_table)
            cur.execute(create_interview_snapshots_table)
            cur.execute(create_profile_plugins_table)
            cur.execute(create_interview_profiles_table)

            # 为现有表添加缺失的列(用于数据库架构升级)
            # 添加 resume_file_id 列到 interviews 表
            try:
                cur.execute("""
                    ALTER TABLE interviews
                    ADD COLUMN IF NOT EXISTS resume_file_id VARCHAR(255)
                """)
                logger.info("✓ 添加 resume_file_id 列")
            except Exception as e:
                logger.debug(f"resume_file_id 列已存在或添加失败: {e}")

            # 添加 resume_text 列到 interviews 表
            try:
                cur.execute("""
                    ALTER TABLE interviews
                    ADD COLUMN IF NOT EXISTS resume_text TEXT
                """)
                logger.info("✓ 添加 resume_text 列")
            except Exception as e:
                logger.debug(f"resume_text 列已存在或添加失败: {e}")

            # 添加 current_message_id 列到 interviews 表
            try:
                cur.execute("""
                    ALTER TABLE interviews
                    ADD COLUMN IF NOT EXISTS current_message_id INTEGER REFERENCES messages(id) ON DELETE SET NULL
                """)
                logger.info("✓ 添加 current_message_id 列")
            except Exception as e:
                logger.debug(f"current_message_id 列已存在或添加失败: {e}")

            # 扩展 recommendation 字段，避免 AI 长文本写入失败
            try:
                cur.execute("""
                    ALTER TABLE evaluations
                    ALTER COLUMN recommendation TYPE TEXT
                """)
                logger.info("✓ 已将 evaluations.recommendation 扩展为 TEXT")
            except Exception as e:
                logger.debug(f"扩展 evaluations.recommendation 失败或已为 TEXT: {e}")

            # 创建索引
            for index_sql in create_indexes:
                cur.execute(index_sql)

            # 为已有库补唯一索引（若历史脏数据导致冲突则跳过，不影响启动）
            try:
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_interview_profiles_interview_id
                    ON interview_profiles(interview_id)
                """)
                logger.info("✓ 添加 interview_profiles.interview_id 唯一索引")
            except Exception as e:
                logger.warning(f"无法创建 interview_profiles.interview_id 唯一索引: {e}")

        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        raise


# ==================== 面试相关操作 ====================

def create_interview(interview_data: dict) -> int:
    """创建面试"""
    sql = """
    INSERT INTO interviews (candidate_name, position, skill_domain, skills,
                           experience_level, duration_minutes, additional_requirements,
                           resume_file_id, resume_text, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            interview_data.get('resume_file_id'),
            interview_data.get('resume_text'),
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


def update_interview_stage(interview_id: int, current_stage: str) -> bool:
    """更新面试当前阶段"""
    sql = "UPDATE interviews SET current_stage = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (current_stage, interview_id))
        return cur.rowcount > 0


def update_interview_current_message(interview_id: int, current_message_id: int) -> bool:
    """更新面试当前消息节点"""
    sql = "UPDATE interviews SET current_message_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (current_message_id, interview_id))
        return cur.rowcount > 0


def get_interview_current_message(interview_id: int) -> Optional[int]:
    """获取面试的当前消息节点ID"""
    sql = "SELECT current_message_id FROM interviews WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        result = cur.fetchone()
        return result['current_message_id'] if result else None


# ==================== 消息相关操作 ====================

def create_message(
    interview_id: int,
    role: str,
    content: str,
    parent_id: Optional[int] = None,
    branch_id: str = 'main'
) -> int:
    """创建消息（支持树形结构）"""
    # 如果没有指定 parent_id，查找该面试和分支的最后一条消息
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
                parent_id = result['id']

    # 计算树路径
    tree_path = []
    if parent_id:
        # 获取父消息的树路径
        sql = "SELECT tree_path FROM messages WHERE id = %s"
        with get_db_cursor() as cur:
            cur.execute(sql, (parent_id,))
            result = cur.fetchone()
            if result and result['tree_path']:
                tree_path = result['tree_path'].copy()
            tree_path.append(parent_id)

    # 插入新消息
    sql = """
    INSERT INTO messages (interview_id, role, content, parent_id, branch_id, tree_path)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id, role, content, parent_id, branch_id, tree_path))
        result = cur.fetchone()
        return result['id']


def get_messages(interview_id: int, limit: int = 100) -> List[dict]:
    """获取面试消息（返回树形结构数据）"""
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
    """Get path messages from root to current message node."""
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
    # 规整数据，避免 AI 输出结构漂移导致数据库写入失败
    dimension_scores = evaluation_data.get('dimension_scores') or {}
    if not isinstance(dimension_scores, dict):
        try:
            dimension_scores = json.loads(dimension_scores)
            if not isinstance(dimension_scores, dict):
                dimension_scores = {}
        except Exception:
            dimension_scores = {}

    strengths = evaluation_data.get('strengths') or []
    if not isinstance(strengths, list):
        strengths = [str(strengths)]
    strengths = [str(item) for item in strengths]

    weaknesses = evaluation_data.get('weaknesses') or []
    if not isinstance(weaknesses, list):
        weaknesses = [str(weaknesses)]
    weaknesses = [str(item) for item in weaknesses]

    recommendation = str(evaluation_data.get('recommendation') or '')
    feedback = str(evaluation_data.get('feedback') or '')

    try:
        overall_score = int(evaluation_data.get('overall_score', 70))
    except Exception:
        overall_score = 70
    overall_score = max(0, min(100, overall_score))

    with get_db_cursor() as cur:
        cur.execute(sql, (
            evaluation_data['interview_id'],
            overall_score,
            Json(dimension_scores, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
            strengths,
            weaknesses,
            recommendation,
            feedback
        ))
        result = cur.fetchone()
        return result['id']


def get_evaluation(interview_id: int) -> Optional[dict]:
    """获取面试评估"""
    sql = "SELECT * FROM evaluations WHERE interview_id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchone()


# ==================== 面试快照相关操作 ====================

def create_snapshot(snapshot_data: dict) -> int:
    """创建面试快照"""
    sql = """
    INSERT INTO interview_snapshots (interview_id, name, description, snapshot_data)
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        import json
        cur.execute(sql, (
            snapshot_data['interview_id'],
            snapshot_data['name'],
            snapshot_data.get('description', ''),
            json.dumps(snapshot_data['snapshot_data'], ensure_ascii=False)
        ))
        result = cur.fetchone()
        return result['id']


def get_snapshots(interview_id: int) -> List[dict]:
    """获取面试的所有快照"""
    sql = """
    SELECT * FROM interview_snapshots
    WHERE interview_id = %s
    ORDER BY created_at DESC
    """
    with get_db_cursor() as cur:
        cur.execute(sql, (interview_id,))
        return cur.fetchall()


def get_snapshot(snapshot_id: int) -> Optional[dict]:
    """获取单个快照详情"""
    sql = "SELECT * FROM interview_snapshots WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (snapshot_id,))
        return cur.fetchone()


def delete_snapshot(snapshot_id: int) -> bool:
    """删除快照"""
    sql = "DELETE FROM interview_snapshots WHERE id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (snapshot_id,))
        return cur.rowcount > 0


def load_snapshot(snapshot_id: int) -> Optional[dict]:
    """加载快照数据（用于恢复）"""
    snapshot = get_snapshot(snapshot_id)
    if snapshot:
        # JSONB 字段会被 psycopg2 自动转换为字典
        snapshot_data = snapshot['snapshot_data']
        # 如果已经是字典,直接返回;如果是字符串,才需要解析
        if isinstance(snapshot_data, dict):
            return snapshot_data
        elif isinstance(snapshot_data, str):
            import json
            return json.loads(snapshot_data)
    return None


# ==================== Prompt配置相关操作 ====================

def save_prompt_config(config_data: dict, config_type: str = 'default') -> int:
    """保存Prompt配置"""
    sql = """
    INSERT INTO prompt_configs (config_type, config_data, updated_at)
    VALUES (%s, %s, CURRENT_TIMESTAMP)
    ON CONFLICT (config_type) DO UPDATE SET
        config_data = EXCLUDED.config_data,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id
    """
    with get_db_cursor() as cur:
        import json
        cur.execute(sql, (config_type, json.dumps(config_data, ensure_ascii=False)))
        result = cur.fetchone()
        return result['id']


def get_prompt_config(config_type: str = 'default') -> Optional[dict]:
    """获取Prompt配置"""
    sql = "SELECT config_data FROM prompt_configs WHERE config_type = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (config_type,))
        result = cur.fetchone()
        if result:
            # JSONB 字段会被 psycopg2 自动转换为字典
            config_data = result['config_data']
            # 如果已经是字典,直接返回;如果是字符串,才需要解析
            if isinstance(config_data, dict):
                return config_data
            elif isinstance(config_data, str):
                import json
                return json.loads(config_data)
        return None


# ==================== 画像插件相关操作 ====================

def create_profile_plugin(plugin_data: dict) -> int:
    """创建画像插件"""
    sql = """
    INSERT INTO profile_plugins (plugin_id, type, name, description, is_system, config)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
    """
    with get_db_cursor() as cur:
        import json
        cur.execute(sql, (
            plugin_data['plugin_id'],
            plugin_data['type'],
            plugin_data['name'],
            plugin_data.get('description', ''),
            plugin_data.get('is_system', False),
            json.dumps(plugin_data.get('config', {}), ensure_ascii=False)
        ))
        result = cur.fetchone()
        return result['id']


def get_profile_plugin(plugin_id: str) -> Optional[dict]:
    """获取单个画像插件"""
    sql = "SELECT * FROM profile_plugins WHERE plugin_id = %s"
    with get_db_cursor() as cur:
        cur.execute(sql, (plugin_id,))
        return cur.fetchone()


def list_profile_plugins(plugin_type: Optional[str] = None, is_system: Optional[bool] = None) -> List[dict]:
    """列出画像插件"""
    sql = "SELECT * FROM profile_plugins WHERE 1=1"
    params = []

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
    """更新画像插件"""
    sql = """
    UPDATE profile_plugins
    SET name = %s, description = %s, config = %s, updated_at = CURRENT_TIMESTAMP
    WHERE plugin_id = %s
    """
    with get_db_cursor() as cur:
        import json
        cur.execute(sql, (
            plugin_data['name'],
            plugin_data.get('description', ''),
            json.dumps(plugin_data.get('config', {}), ensure_ascii=False),
            plugin_id
        ))
        return cur.rowcount > 0


def delete_profile_plugin(plugin_id: str) -> bool:
    """删除画像插件(只能删除非系统预设的)"""
    sql = "DELETE FROM profile_plugins WHERE plugin_id = %s AND is_system = FALSE"
    with get_db_cursor() as cur:
        cur.execute(sql, (plugin_id,))
        return cur.rowcount > 0


def apply_interview_profile(interview_id: int, position_plugin_id: str, interviewer_plugin_id: str, custom_config: dict = None) -> int:
    """应用画像到面试"""
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
    with get_db_cursor() as cur:
        import json
        custom_config_json = json.dumps(custom_config or {}, ensure_ascii=False)

        cur.execute(update_sql, (
            position_plugin_id,
            interviewer_plugin_id,
            custom_config_json,
            interview_id,
        ))
        result = cur.fetchone()
        if result:
            return result['id']

        cur.execute(insert_sql, (
            interview_id,
            position_plugin_id,
            interviewer_plugin_id,
            custom_config_json,
        ))
        result = cur.fetchone()
        return result['id']


def get_interview_profile(interview_id: int) -> Optional[dict]:
    """获取面试的画像配置"""
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


def init_default_profiles():
    """初始化系统预设画像"""
    default_profiles = [
        # 岗位画像
        {
            'plugin_id': 'position_frontend_junior',
            'type': 'position',
            'name': '初级前端工程师',
            'description': '适合1-3年经验的前端工程师岗位',
            'is_system': True,
            'config': {
                'ability_weights': {
                    'technical': 0.6,
                    'communication': 0.15,
                    'problem_solving': 0.15,
                    'learning_potential': 0.1
                },
                'skill_requirements': {
                    'core_skills': ['HTML/CSS', 'JavaScript', 'Vue.js/React'],
                    'weights': {'HTML/CSS': 0.3, 'JavaScript': 0.4, 'Vue.js/React': 0.3}
                },
                'interview_strategy': {
                    'stages': [
                        {'stage': 'welcome', 'time_allocation': 2, 'focus': '建立融洽关系'},
                        {'stage': 'technical', 'time_allocation': 15, 'focus': '基础知识考察'},
                        {'stage': 'scenario', 'time_allocation': 10, 'focus': '实际问题解决'},
                        {'stage': 'closing', 'time_allocation': 3, 'focus': '总结和答疑'}
                    ]
                }
            }
        },
        {
            'plugin_id': 'position_frontend_mid',
            'type': 'position',
            'name': '中级前端工程师',
            'description': '适合3-5年经验的前端工程师岗位',
            'is_system': True,
            'config': {
                'ability_weights': {
                    'technical': 0.5,
                    'communication': 0.2,
                    'problem_solving': 0.2,
                    'learning_potential': 0.1
                },
                'skill_requirements': {
                    'core_skills': ['Vue.js', 'TypeScript', '工程化'],
                    'weights': {'Vue.js': 0.35, 'TypeScript': 0.35, '工程化': 0.3}
                },
                'interview_strategy': {
                    'stages': [
                        {'stage': 'welcome', 'time_allocation': 2, 'focus': '建立融洽关系'},
                        {'stage': 'technical', 'time_allocation': 20, 'focus': '深度技术能力'},
                        {'stage': 'scenario', 'time_allocation': 15, 'focus': '复杂场景分析'},
                        {'stage': 'closing', 'time_allocation': 3, 'focus': '总结和答疑'}
                    ]
                }
            }
        },
        {
            'plugin_id': 'position_backend_senior',
            'type': 'position',
            'name': '高级后端工程师',
            'description': '适合5年以上经验的后端工程师岗位',
            'is_system': True,
            'config': {
                'ability_weights': {
                    'technical': 0.4,
                    'communication': 0.2,
                    'problem_solving': 0.25,
                    'learning_potential': 0.15
                },
                'skill_requirements': {
                    'core_skills': ['架构设计', '性能优化', '系统设计'],
                    'weights': {'架构设计': 0.4, '性能优化': 0.3, '系统设计': 0.3}
                },
                'interview_strategy': {
                    'stages': [
                        {'stage': 'welcome', 'time_allocation': 3, 'focus': '建立融洽关系'},
                        {'stage': 'technical', 'time_allocation': 25, 'focus': '架构和技术深度'},
                        {'stage': 'scenario', 'time_allocation': 20, 'focus': '系统设计能力'},
                        {'stage': 'closing', 'time_allocation': 5, 'focus': '总结和答疑'}
                    ]
                }
            }
        },
        # 面试官画像
        {
            'plugin_id': 'interviewer_tech_expert',
            'type': 'interviewer',
            'name': '技术专家型面试官',
            'description': '注重技术深度,提问严谨,逻辑性强',
            'is_system': True,
            'config': {
                'style': {
                    'questioning_style': 'deep_technical',
                    'pace': 'moderate',
                    'interaction': 'two_way',
                    'strictness': 0.7
                },
                'characteristics': ['技术专家型', '注重实战', '逻辑严密'],
                'prompt_templates': {
                    'technical_question': '请从技术实现角度详细分析{topic},并说明你的思路',
                    'follow_up': '你提到的{point},能展开说说具体实现吗?',
                    'clarification': '能详细解释一下{concept}吗?'
                }
            }
        },
        {
            'plugin_id': 'interviewer_friendly',
            'type': 'interviewer',
            'name': '亲和引导型面试官',
            'description': '氛围轻松,善于引导,注重潜力',
            'is_system': True,
            'config': {
                'style': {
                    'questioning_style': 'guided',
                    'pace': 'slow',
                    'interaction': 'two_way',
                    'strictness': 0.3
                },
                'characteristics': ['亲和力强', '善于引导', '注重潜力'],
                'prompt_templates': {
                    'technical_question': '能不能跟我分享一下你对{topic}的理解?',
                    'follow_up': '这个观点很有意思,能多说一点吗?',
                    'clarification': '如果我没理解错,你的意思是{concept},对吗?'
                }
            }
        },
        {
            'plugin_id': 'interviewer_behavioral',
            'type': 'interviewer',
            'name': '行为导向型面试官',
            'description': '关注过往经历和行为模式',
            'is_system': True,
            'config': {
                'style': {
                    'questioning_style': 'behavioral',
                    'pace': 'moderate',
                    'interaction': 'two_way',
                    'strictness': 0.5
                },
                'characteristics': ['行为导向', '注重经验', '关注细节'],
                'prompt_templates': {
                    'technical_question': '请举一个你在项目中处理{topic}的具体例子',
                    'follow_up': '当时你是如何处理{situation}的?',
                    'clarification': '能具体说说当时的背景和结果吗?'
                }
            }
        }
    ]

    for profile in default_profiles:
        try:
            create_profile_plugin(profile)
        except Exception as e:
            logger.warning(f"创建预设画像失败 {profile['name']}: {e}")
            continue

    logger.info("系统预设画像初始化完成")
