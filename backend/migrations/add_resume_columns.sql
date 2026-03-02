-- 添加 resume_file_id 和 resume_text 列到 interviews 表
-- 执行方式: psql -U postgres -d interview_db -f migrations/add_resume_columns.sql

-- 添加 resume_file_id 列
ALTER TABLE interviews
ADD COLUMN IF NOT EXISTS resume_file_id VARCHAR(255);

-- 添加 resume_text 列 (存储解析后的简历文本)
ALTER TABLE interviews
ADD COLUMN IF NOT EXISTS resume_text TEXT;

-- 添加注释
COMMENT ON COLUMN interviews.resume_file_id IS '上传的简历文件ID';
COMMENT ON COLUMN interviews.resume_text IS '解析后的简历文本内容';
