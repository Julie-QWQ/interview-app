"""
SQL 安全工具模块
提供安全的 SQL 查询构建工具，防止 SQL 注入
"""
import logging
import re
from typing import Any, Dict, List, Set, Optional, Tuple

logger = logging.getLogger(__name__)


class SQLSafeBuilder:
    """
    安全的 SQL 查询构建器

    提供安全的字段验证和查询构建功能，防止 SQL 注入
    """

    def __init__(self, allowed_fields: Optional[Set[str]] = None):
        """
        初始化 SQL 构建器

        Args:
            allowed_fields: 允许的字段白名单，如果为 None 则不进行限制
        """
        self.allowed_fields = allowed_fields or set()
        self._sql_identifier_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    def validate_field_name(self, field_name: str) -> bool:
        """
        验证字段名是否安全

        Args:
            field_name: 要验证的字段名

        Returns:
            True if field_name is safe, False otherwise
        """
        # 检查是否在白名单中
        if self.allowed_fields and field_name not in self.allowed_fields:
            logger.warning(f"Field '{field_name}' not in allowed fields")
            return False

        # 检查字段名格式（只允许字母、数字、下划线，且不能以数字开头）
        if not self._sql_identifier_pattern.match(field_name):
            logger.warning(f"Field '{field_name}' contains unsafe characters")
            return False

        # 检查 SQL 关键字
        sql_keywords = {
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'UNION', 'OR', 'AND', 'WHERE', 'FROM', 'JOIN', 'EXEC', 'EXECUTE'
        }
        if field_name.upper() in sql_keywords:
            logger.warning(f"Field '{field_name}' is a SQL keyword")
            return False

        return True

    def validate_field_names(self, field_names: List[str]) -> bool:
        """
        批量验证字段名

        Args:
            field_names: 要验证的字段名列表

        Returns:
            True if all field names are safe, False otherwise
        """
        return all(self.validate_field_name(field) for field in field_names)

    def build_update_clause(
        self,
        updates: Dict[str, Any],
        table_name: str,
        where_clause: str = "id = %s"
    ) -> Tuple[str, List[Any]]:
        """
        安全地构建 UPDATE 语句

        Args:
            updates: 要更新的字段字典 {field_name: new_value}
            table_name: 表名
            where_clause: WHERE 子句（默认为 "id = %s"）

        Returns:
            (sql_query, params) 元组

        Raises:
            ValueError: 如果字段名不安全

        Example:
            >>> builder = SQLSafeBuilder({'name', 'email', 'status'})
            >>> sql, params = builder.build_update_clause(
            ...     {'name': 'John', 'status': 'active'},
            ...     'users'
            ... )
            >>> print(sql)
            UPDATE users SET name = %s, status = %s WHERE id = %s
            >>> print(params)
            ['John', 'active']
        """
        # 验证所有字段名
        field_names = list(updates.keys())
        if not self.validate_field_names(field_names):
            unsafe_fields = [
                f for f in field_names
                if not self.validate_field_name(f)
            ]
            raise ValueError(
                f"Unsafe or disallowed field names: {', '.join(unsafe_fields)}"
            )

        # 构建 SET 子句
        set_clauses = [f"{field} = %s" for field in field_names]
        params = list(updates.values())

        # 构建完整的 SQL 语句
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {where_clause}"

        return sql, params

    def build_insert_statement(
        self,
        table_name: str,
        data: Dict[str, Any],
        returning: Optional[str] = None
    ) -> Tuple[str, List[Any]]:
        """
        安全地构建 INSERT 语句

        Args:
            table_name: 表名
            data: 要插入的数据字典 {field_name: value}
            returning: RETURNING 子句（如 "id" 或 "id, created_at"）

        Returns:
            (sql_query, params) 元组

        Raises:
            ValueError: 如果字段名不安全

        Example:
            >>> builder = SQLSafeBuilder({'name', 'email'})
            >>> sql, params = builder.build_insert_statement(
            ...     'users',
            ...     {'name': 'John', 'email': 'john@example.com'}
            ... )
            >>> print(sql)
            INSERT INTO users (name, email) VALUES (%s, %s)
            >>> print(params)
            ['John', 'john@example.com']
        """
        # 验证所有字段名
        field_names = list(data.keys())
        if not self.validate_field_names(field_names):
            unsafe_fields = [
                f for f in field_names
                if not self.validate_field_name(f)
            ]
            raise ValueError(
                f"Unsafe or disallowed field names: {', '.join(unsafe_fields)}"
            )

        # 构建 INSERT 语句
        columns = ', '.join(field_names)
        placeholders = ', '.join(['%s'] * len(field_names))
        params = list(data.values())

        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        if returning:
            sql += f" RETURNING {returning}"

        return sql, params


class SQLValidator:
    """
    SQL 验证工具类
    """

    @staticmethod
    def validate_table_name(table_name: str) -> bool:
        """
        验证表名是否安全

        Args:
            table_name: 要验证的表名

        Returns:
            True if table_name is safe, False otherwise
        """
        pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        return bool(pattern.match(table_name))

    @staticmethod
    def validate_order_by(order_by: str, allowed_fields: Set[str]) -> bool:
        """
        验证 ORDER BY 子句

        Args:
            order_by: ORDER BY 字段名（可能包含 DESC/ASC）
            allowed_fields: 允许的字段集合

        Returns:
            True if order_by is safe, False otherwise
        """
        # 分离字段名和排序方向
        parts = order_by.rsplit(' ', 1)
        field = parts[0]
        direction = parts[1].upper() if len(parts) > 1 else None

        # 验证字段名
        if field not in allowed_fields:
            return False

        # 验证排序方向
        if direction is not None and direction not in ('ASC', 'DESC'):
            return False

        return True

    @staticmethod
    def sanitize_like_pattern(pattern: str) -> str:
        """
        清理 LIKE 模式，防止通配符注入

        Args:
            pattern: LIKE 搜索模式

        Returns:
            清理后的模式（转义了特殊的通配符）

        Example:
            >>> SQLValidator.sanitize_like_pattern("100%")
            '100\\%'
            >>> SQLValidator.sanitize_like_pattern("user_data")
            'user_data'
        """
        # 转义 LIKE 通配符
        escape_chars = {'%', '_', '\\'}
        result = []
        for char in pattern:
            if char in escape_chars:
                result.append('\\' + char)
            else:
                result.append(char)
        return ''.join(result)


# 预定义的表字段白名单
INTERVIEW_ALLOWED_FIELDS = {
    'id', 'candidate_name', 'position', 'skill_domain', 'skills',
    'experience_level', 'duration_minutes', 'additional_requirements',
    'resume_file_id', 'resume_text', 'status', 'current_stage',
    'current_message_id', 'created_at', 'updated_at', 'completed_at'
}

MESSAGE_ALLOWED_FIELDS = {
    'id', 'interview_id', 'role', 'content', 'parent_id',
    'branch_id', 'tree_path', 'is_active', 'timestamp'
}

SNAPSHOT_ALLOWED_FIELDS = {
    'id', 'interview_id', 'name', 'description', 'snapshot_data',
    'created_at'
}

# 创建预配置的构建器实例
interview_builder = SQLSafeBuilder(INTERVIEW_ALLOWED_FIELDS)
message_builder = SQLSafeBuilder(MESSAGE_ALLOWED_FIELDS)
snapshot_builder = SQLSafeBuilder(SNAPSHOT_ALLOWED_FIELDS)
