-- 添加树形结构支持到 messages 表
-- 运行此脚本来升级现有数据库

-- 添加新字段（如果不存在）
DO $$
BEGIN
    -- 添加 parent_id 字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'parent_id'
    ) THEN
        ALTER TABLE messages ADD COLUMN parent_id INTEGER REFERENCES messages(id) ON DELETE CASCADE;
    END IF;

    -- 添加 branch_id 字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'branch_id'
    ) THEN
        ALTER TABLE messages ADD COLUMN branch_id VARCHAR(100) DEFAULT 'main';
    END IF;

    -- 添加 tree_path 字段（用于快速路径查询）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'tree_path'
    ) THEN
        ALTER TABLE messages ADD COLUMN tree_path TEXT[] DEFAULT '{}';
    END IF;

    -- 添加 is_active 字段（用于标记当前活跃路径）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'messages' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE messages ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;
END $$;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_messages_parent_id ON messages(parent_id);
CREATE INDEX IF NOT EXISTS idx_messages_branch_id ON messages(branch_id);
CREATE INDEX IF NOT EXISTS idx_messages_is_active ON messages(is_active);

-- 为现有数据初始化默认值
-- 将现有的线性消息转换为树形结构（每个消息的parent_id是前一条消息）
UPDATE messages m1
SET parent_id = (
    SELECT m2.id
    FROM messages m2
    WHERE m2.interview_id = m1.interview_id
    AND m2.timestamp < m1.timestamp
    ORDER BY m2.timestamp DESC
    LIMIT 1
)
WHERE parent_id IS NULL;

-- 初始化 branch_id 为 'main'
UPDATE messages SET branch_id = 'main' WHERE branch_id IS NULL;

-- 初始化 is_active 为 true
UPDATE messages SET is_active = true WHERE is_active IS NULL;

COMMENT ON COLUMN messages.parent_id IS '父消息ID，用于构建树形结构';
COMMENT ON COLUMN messages.branch_id IS '分支ID，用于标识对话分支';
COMMENT ON COLUMN messages.tree_path IS '从根到当前节点的路径ID数组';
COMMENT ON COLUMN messages.is_active IS '是否在当前活跃路径上';
