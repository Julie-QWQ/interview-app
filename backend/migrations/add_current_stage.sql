-- 添加 current_stage 字段到 interviews 表
ALTER TABLE interviews ADD COLUMN IF NOT EXISTS current_stage VARCHAR(50) DEFAULT 'welcome';

-- 为现有记录设置默认值
UPDATE interviews SET current_stage = 'welcome' WHERE current_stage IS NULL;

-- 添加索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_interviews_current_stage ON interviews(current_stage);
