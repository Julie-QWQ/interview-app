"""
画像插件API接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.db.database import (
    create_profile_plugin,
    get_profile_plugin,
    list_profile_plugins,
    update_profile_plugin,
    delete_profile_plugin,
    apply_interview_profile,
    get_interview_profile,
    init_default_profiles
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profiles", tags=["画像管理"])


# ==================== 数据模型 ====================

class ProfilePluginCreate(BaseModel):
    plugin_id: str
    type: str  # position | interviewer
    name: str
    description: Optional[str] = None
    is_system: Optional[bool] = False
    config: Optional[dict] = None


class ProfilePluginUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    config: Optional[dict] = None


class InterviewProfileApply(BaseModel):
    position_plugin_id: str
    interviewer_plugin_id: str
    custom_config: Optional[dict] = None


# ==================== API接口 ====================

@router.on_event("startup")
async def startup_event():
    """服务启动时初始化系统预设画像"""
    try:
        init_default_profiles()
    except Exception as e:
        logger.warning(f"初始化预设画像失败: {e}")


@router.get("/plugins")
async def list_plugins(
    type: Optional[str] = Query(None, description="插件类型: position/interviewer"),
    is_system: Optional[bool] = Query(None, description="是否系统预设")
):
    """获取画像插件列表"""
    try:
        plugins = list_profile_plugins(plugin_type=type, is_system=is_system)
        return {
            "success": True,
            "data": plugins
        }
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取插件列表失败")


@router.post("/plugins")
async def create_plugin(plugin: ProfilePluginCreate):
    """创建自定义画像插件"""
    try:
        # 检查是否已存在
        existing = get_profile_plugin(plugin.plugin_id)
        if existing:
            raise HTTPException(status_code=400, detail="插件ID已存在")

        plugin_id = create_profile_plugin(plugin.dict())
        return {
            "success": True,
            "message": "创建成功",
            "data": {"plugin_id": plugin.plugin_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建插件失败: {e}")
        raise HTTPException(status_code=500, detail="创建插件失败")


@router.get("/plugins/{plugin_id}")
async def get_plugin(plugin_id: str):
    """获取插件详情"""
    try:
        plugin = get_profile_plugin(plugin_id)
        if not plugin:
            raise HTTPException(status_code=404, detail="插件不存在")
        return {
            "success": True,
            "data": plugin
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取插件详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取插件详情失败")


@router.put("/plugins/{plugin_id}")
async def update_plugin(plugin_id: str, plugin: ProfilePluginUpdate):
    """更新插件配置"""
    try:
        # 检查插件是否存在
        existing = get_profile_plugin(plugin_id)
        if not existing:
            raise HTTPException(status_code=404, detail="插件不存在")

        # 系统预设插件不允许修改
        if existing['is_system']:
            raise HTTPException(status_code=403, detail="系统预设插件不允许修改")

        success = update_profile_plugin(plugin_id, plugin.dict())
        if not success:
            raise HTTPException(status_code=500, detail="更新失败")

        return {
            "success": True,
            "message": "更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新插件失败: {e}")
        raise HTTPException(status_code=500, detail="更新插件失败")


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str):
    """删除自定义插件"""
    try:
        # 检查插件是否存在
        existing = get_profile_plugin(plugin_id)
        if not existing:
            raise HTTPException(status_code=404, detail="插件不存在")

        # 系统预设插件不允许删除
        if existing['is_system']:
            raise HTTPException(status_code=403, detail="系统预设插件不允许删除")

        success = delete_profile_plugin(plugin_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除失败")

        return {
            "success": True,
            "message": "删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除插件失败: {e}")
        raise HTTPException(status_code=500, detail="删除插件失败")


@router.post("/interviews/{interview_id}/apply")
async def apply_profiles(interview_id: int, data: InterviewProfileApply):
    """应用画像到面试"""
    try:
        # 检查插件是否存在
        position_plugin = get_profile_plugin(data.position_plugin_id)
        if not position_plugin:
            raise HTTPException(status_code=404, detail=f"岗位插件 {data.position_plugin_id} 不存在")

        interviewer_plugin = get_profile_plugin(data.interviewer_plugin_id)
        if not interviewer_plugin:
            raise HTTPException(status_code=404, detail=f"面试官插件 {data.interviewer_plugin_id} 不存在")

        profile_id = apply_interview_profile(
            interview_id,
            data.position_plugin_id,
            data.interviewer_plugin_id,
            data.custom_config
        )

        return {
            "success": True,
            "message": "应用成功",
            "data": {"profile_id": profile_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用画像失败: {e}")
        raise HTTPException(status_code=500, detail="应用画像失败")


@router.get("/interviews/{interview_id}")
async def get_interview_profiles(interview_id: int):
    """获取面试的画像配置"""
    try:
        profile = get_interview_profile(interview_id)
        if not profile:
            raise HTTPException(status_code=404, detail="该面试未配置画像")

        return {
            "success": True,
            "data": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取面试画像失败: {e}")
        raise HTTPException(status_code=500, detail="获取面试画像失败")
