"""Expression analysis service for multimodal interview signals."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, cast


FILLER_WORDS = ("嗯", "啊", "哦", "额", "呃", "那个", "就是", "然后")


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, float(value)))


def _safe_mean(values: Iterable[float]) -> float:
    normalized = [float(value) for value in values if value is not None]
    if not normalized:
        return 0.0
    return float(sum(normalized) / len(normalized))


def _safe_stdev(values: Iterable[float]) -> float:
    normalized = [float(value) for value in values if value is not None]
    if len(normalized) < 2:
        return 0.0
    return float(statistics.pstdev(normalized))


def _extract_timestamp(record: Dict[str, Any]) -> str:
    return (
        str(record.get("ended_at") or "").strip()
        or str(record.get("started_at") or "").strip()
        or str(record.get("client_ended_at") or "").strip()
        or str(record.get("client_started_at") or "").strip()
    )


@dataclass
class ExpressionAnalysisResult:
    interview_id: int
    overall_score: int
    confidence_level: str
    confidence_score: int
    modality_coverage: Dict[str, bool]
    metrics: Dict[str, Any]
    dimension_scores: Dict[str, int]
    evidence_summary: List[str]
    risk_flags: List[str]
    narrative_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_id": self.interview_id,
            "overall_score": self.overall_score,
            "confidence_level": self.confidence_level,
            "confidence_score": self.confidence_score,
            "modality_coverage": self.modality_coverage,
            "metrics": self.metrics,
            "dimension_scores": self.dimension_scores,
            "evidence_summary": self.evidence_summary,
            "risk_flags": self.risk_flags,
            "narrative_summary": self.narrative_summary,
        }


class ExpressionAnalyzerService:
    def __init__(self, settings):
        self.settings = settings

    def _config(self) -> Dict[str, Any]:
        config = self.settings.expression_analysis_config
        return cast(Dict[str, Any], config)

    @staticmethod
    def _normalize_audio_segment(payload: Dict[str, Any]) -> Dict[str, Any]:
        content = str(payload.get("transcript_text") or payload.get("text") or "").strip()
        text_length = int(payload.get("text_length") or len(content))
        duration_ms = int(payload.get("duration_ms") or 0)
        speech_duration_ms = int(payload.get("speech_duration_ms") or duration_ms)
        pause_ratio = float(payload.get("pause_ratio") or 0.0)
        avg_volume = float(payload.get("avg_volume") or payload.get("mean_rms") or 0.0)
        volume_variation = float(payload.get("volume_variation") or payload.get("rms_stddev") or 0.0)
        filler_count = int(payload.get("filler_count") or 0)
        if not filler_count and content:
            filler_count = sum(content.count(word) for word in FILLER_WORDS)
        sentence_count = int(payload.get("sentence_count") or 0)
        if not sentence_count and content:
            sentence_count = max(
                1,
                sum(content.count(mark) for mark in ("。", "！", "？", ".", "!", "?")),
            )
        words_per_minute = float(payload.get("speech_rate_wpm") or 0.0)
        if words_per_minute <= 0 and duration_ms > 0 and text_length > 0:
            words_per_minute = (text_length / max(duration_ms / 60000.0, 0.001))
        interruption_recovery_ms = int(payload.get("interruption_recovery_ms") or 0)
        self_correction_count = int(payload.get("self_correction_count") or 0)
        if not self_correction_count and content:
            self_correction_count = sum(content.count(word) for word in ("不是", "重说", "更正", "我的意思是"))
        repetition_ratio = float(payload.get("repetition_ratio") or 0.0)
        if repetition_ratio <= 0 and content:
            tokens = [token for token in content.replace("，", " ").replace(",", " ").split() if token]
            if tokens:
                token_counter = Counter(tokens)
                repetition_ratio = max(token_counter.values()) / max(len(tokens), 1)
        return {
            "segment_id": str(payload.get("segment_id") or "").strip(),
            "stage": str(payload.get("stage") or "").strip(),
            "source": str(payload.get("source") or "manual_voice").strip(),
            "started_at": str(payload.get("client_started_at") or payload.get("started_at") or "").strip(),
            "ended_at": str(payload.get("client_ended_at") or payload.get("ended_at") or "").strip(),
            "duration_ms": duration_ms,
            "speech_duration_ms": speech_duration_ms,
            "pause_ratio": pause_ratio,
            "avg_volume": avg_volume,
            "volume_variation": volume_variation,
            "filler_count": filler_count,
            "sentence_count": sentence_count,
            "text_length": text_length,
            "speech_rate_wpm": words_per_minute,
            "interruption_recovery_ms": interruption_recovery_ms,
            "self_correction_count": self_correction_count,
            "repetition_ratio": repetition_ratio,
            "transcript_text": content,
        }

    @staticmethod
    def _normalize_video_window(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "window_id": str(payload.get("window_id") or "").strip(),
            "stage": str(payload.get("stage") or "").strip(),
            "started_at": str(payload.get("started_at") or "").strip(),
            "ended_at": str(payload.get("ended_at") or "").strip(),
            "sample_count": int(payload.get("sample_count") or 0),
            "face_present_rate": float(payload.get("face_present_rate") or 0.0),
            "gaze_aversion_rate": float(payload.get("gaze_aversion_rate") or 0.0),
            "head_jitter": float(payload.get("head_jitter") or 0.0),
            "face_center_stability": float(payload.get("face_center_stability") or 0.0),
            "mouth_activity_stability": float(payload.get("mouth_activity_stability") or 0.0),
            "expression_intensity_variance": float(payload.get("expression_intensity_variance") or 0.0),
            "brightness": float(payload.get("brightness") or 0.0),
            "motion_intensity": float(payload.get("motion_intensity") or 0.0),
            "face_area_rate": float(payload.get("face_area_rate") or 0.0),
            "detector_type": str(payload.get("detector_type") or "heuristic").strip(),
        }

    def normalize_audio_segment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._normalize_audio_segment(payload)

    def normalize_video_window(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._normalize_video_window(payload)

    def analyze(
        self,
        interview_id: int,
        audio_segments: List[Dict[str, Any]],
        video_windows: List[Dict[str, Any]],
    ) -> ExpressionAnalysisResult:
        metrics = self._aggregate_metrics(audio_segments, video_windows)
        dimension_scores = self._score_dimensions(metrics)
        weights = self._config()["weights"]
        overall_score = round(
            sum(dimension_scores[name] * float(weights.get(name, 0.0)) for name in dimension_scores)
        )
        confidence_score, confidence_level = self._confidence(metrics)
        modality_coverage = {
            "audio": bool(audio_segments),
            "video": bool(video_windows),
            "text": bool(metrics["audio"].get("transcript_chars")),
        }
        evidence_summary = self._build_evidence(metrics, dimension_scores)
        risk_flags = self._build_risk_flags(metrics, dimension_scores)
        narrative_summary = self._build_summary(dimension_scores, confidence_level, evidence_summary, risk_flags)
        return ExpressionAnalysisResult(
            interview_id=interview_id,
            overall_score=int(overall_score),
            confidence_level=confidence_level,
            confidence_score=int(confidence_score),
            modality_coverage=modality_coverage,
            metrics=metrics,
            dimension_scores={key: int(value) for key, value in dimension_scores.items()},
            evidence_summary=evidence_summary,
            risk_flags=risk_flags,
            narrative_summary=narrative_summary,
        )

    def _aggregate_metrics(
        self,
        audio_segments: List[Dict[str, Any]],
        video_windows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        transcript_chars = sum(int(item.get("text_length") or 0) for item in audio_segments)
        transcript_text = " ".join(item.get("transcript_text") or "" for item in audio_segments).strip()
        total_duration_ms = sum(int(item.get("duration_ms") or 0) for item in audio_segments)
        speaking_duration_ms = sum(int(item.get("speech_duration_ms") or 0) for item in audio_segments)
        total_sentences = sum(int(item.get("sentence_count") or 0) for item in audio_segments)
        filler_count = sum(int(item.get("filler_count") or 0) for item in audio_segments)
        self_correction_count = sum(int(item.get("self_correction_count") or 0) for item in audio_segments)

        audio_metrics = {
            "segment_count": len(audio_segments),
            "total_duration_ms": total_duration_ms,
            "speaking_duration_ms": speaking_duration_ms,
            "avg_pause_ratio": _safe_mean(item.get("pause_ratio") or 0 for item in audio_segments),
            "avg_volume": _safe_mean(item.get("avg_volume") or 0 for item in audio_segments),
            "volume_variation": _safe_mean(item.get("volume_variation") or 0 for item in audio_segments),
            "speech_rate_wpm": _safe_mean(item.get("speech_rate_wpm") or 0 for item in audio_segments),
            "filler_density": filler_count / max(transcript_chars, 1),
            "self_correction_density": self_correction_count / max(transcript_chars, 1),
            "repetition_ratio": _safe_mean(item.get("repetition_ratio") or 0 for item in audio_segments),
            "interruption_recovery_ms": _safe_mean(item.get("interruption_recovery_ms") or 0 for item in audio_segments),
            "transcript_chars": transcript_chars,
            "sentence_count": total_sentences,
            "avg_sentence_length": transcript_chars / max(total_sentences, 1),
            "structure_score": self._structure_score(transcript_text),
        }

        video_metrics = {
            "window_count": len(video_windows),
            "face_present_rate": _safe_mean(item.get("face_present_rate") or 0 for item in video_windows),
            "gaze_aversion_rate": _safe_mean(item.get("gaze_aversion_rate") or 0 for item in video_windows),
            "head_jitter": _safe_mean(item.get("head_jitter") or 0 for item in video_windows),
            "face_center_stability": _safe_mean(item.get("face_center_stability") or 0 for item in video_windows),
            "mouth_activity_stability": _safe_mean(item.get("mouth_activity_stability") or 0 for item in video_windows),
            "expression_intensity_variance": _safe_mean(
                item.get("expression_intensity_variance") or 0 for item in video_windows
            ),
            "motion_intensity": _safe_mean(item.get("motion_intensity") or 0 for item in video_windows),
            "brightness": _safe_mean(item.get("brightness") or 0 for item in video_windows),
            "face_area_rate": _safe_mean(item.get("face_area_rate") or 0 for item in video_windows),
        }

        timeline = sorted(
            [
                {
                    "kind": "audio",
                    "id": item.get("segment_id"),
                    "timestamp": _extract_timestamp(item),
                }
                for item in audio_segments
            ]
            + [
                {
                    "kind": "video",
                    "id": item.get("window_id"),
                    "timestamp": _extract_timestamp(item),
                }
                for item in video_windows
            ],
            key=lambda item: (item["timestamp"], item["kind"], item["id"] or ""),
        )

        return {
            "audio": audio_metrics,
            "video": video_metrics,
            "timeline": timeline,
        }

    @staticmethod
    def _structure_score(text: str) -> float:
        normalized = str(text or "").strip()
        if not normalized:
            return 30.0
        score = 55.0
        if any(marker in normalized for marker in ("首先", "然后", "最后", "第一", "第二", "总结")):
            score += 20.0
        if any(marker in normalized for marker in ("因为", "所以", "例如", "比如", "方案")):
            score += 15.0
        if len(normalized) >= 120:
            score += 10.0
        return _clamp(score)

    def _score_dimensions(self, metrics: Dict[str, Any]) -> Dict[str, int]:
        audio = metrics["audio"]
        video = metrics["video"]

        fluency = 75.0
        speech_rate = audio["speech_rate_wpm"]
        if speech_rate:
            fluency -= min(abs(speech_rate - 220.0) * 0.12, 18.0)
        fluency -= min(audio["avg_pause_ratio"] * 42.0, 18.0)
        fluency -= min(audio["filler_density"] * 2500.0, 15.0)
        fluency -= min(audio["self_correction_density"] * 2200.0, 10.0)
        fluency += min(audio["structure_score"] * 0.12, 8.0)

        clarity = 72.0
        clarity += min(audio["structure_score"] * 0.18, 14.0)
        clarity -= min(audio["repetition_ratio"] * 30.0, 12.0)
        clarity -= min(audio["volume_variation"] * 150.0, 12.0)
        if audio["avg_sentence_length"]:
            clarity -= min(abs(audio["avg_sentence_length"] - 28.0) * 0.4, 10.0)

        confidence = 70.0
        confidence += min(video["face_present_rate"] * 18.0, 18.0)
        confidence -= min(video["gaze_aversion_rate"] * 20.0, 18.0)
        confidence -= min(video["head_jitter"] * 40.0, 14.0)
        confidence += min(video["face_center_stability"] * 15.0, 12.0)
        confidence -= min(audio["interruption_recovery_ms"] / 180.0, 10.0)

        composure = 74.0
        composure += min(video["mouth_activity_stability"] * 18.0, 12.0)
        composure -= min(video["expression_intensity_variance"] * 35.0, 12.0)
        composure -= min(video["motion_intensity"] * 35.0, 10.0)
        composure -= min(audio["volume_variation"] * 120.0, 10.0)
        composure -= min(audio["avg_pause_ratio"] * 20.0, 8.0)

        if not video["window_count"]:
            confidence = confidence * 0.82 + 8.0
            composure = composure * 0.85 + 8.0
        if not audio["segment_count"]:
            fluency = fluency * 0.7 + 10.0
            clarity = clarity * 0.7 + 12.0

        return {
            "fluency": int(round(_clamp(fluency))),
            "clarity": int(round(_clamp(clarity))),
            "confidence": int(round(_clamp(confidence))),
            "composure": int(round(_clamp(composure))),
            "speech_rate": int(round(_clamp(100.0 - min(abs(speech_rate - 220.0) * 0.2, 45.0)))),
        }

    def _confidence(self, metrics: Dict[str, Any]) -> tuple[int, str]:
        config = self._config()
        audio_segments = metrics["audio"]["segment_count"]
        video_windows = metrics["video"]["window_count"]
        sample_score = min(audio_segments * 26 + video_windows * 18, 100)
        if audio_segments < config["audio_min_segments"]:
            sample_score -= 20
        if video_windows < config["video_min_windows"]:
            sample_score -= 10
        if not metrics["audio"]["transcript_chars"]:
            sample_score -= 15
        sample_score = int(_clamp(sample_score))
        if sample_score >= 75:
            return sample_score, "high"
        if sample_score >= 45:
            return sample_score, "medium"
        return sample_score, "low"

    def _build_evidence(self, metrics: Dict[str, Any], dimension_scores: Dict[str, int]) -> List[str]:
        audio = metrics["audio"]
        video = metrics["video"]
        evidence: List[str] = []
        if audio["segment_count"]:
            evidence.append(
                f"记录到 {audio['segment_count']} 段语音，平均语速约 {audio['speech_rate_wpm']:.0f} 字/分钟，停顿占比 {audio['avg_pause_ratio']:.2f}。"
            )
            evidence.append(
                f"文本组织度评分约 {audio['structure_score']:.0f}，口头禅密度 {audio['filler_density']:.3f}，平均句长 {audio['avg_sentence_length']:.1f}。"
            )
        if video["window_count"]:
            evidence.append(
                f"记录到 {video['window_count']} 个视频窗口，脸部在场率 {video['face_present_rate']:.2f}，视线偏移率 {video['gaze_aversion_rate']:.2f}。"
            )
            evidence.append(
                f"头部抖动 {video['head_jitter']:.3f}，面部稳定性 {video['face_center_stability']:.2f}，表情变化强度 {video['expression_intensity_variance']:.2f}。"
            )
        if not evidence:
            evidence.append("当前仅有少量表达数据，报告主要依据文本和少量元数据推断。")
        strongest = max(dimension_scores, key=lambda k: dimension_scores[k])
        evidence.append(f"当前最强维度为 {strongest}，得分 {dimension_scores[strongest]}。")
        return evidence

    @staticmethod
    def _build_risk_flags(metrics: Dict[str, Any], dimension_scores: Dict[str, int]) -> List[str]:
        audio = metrics["audio"]
        video = metrics["video"]
        risks: List[str] = []
        if audio["speech_rate_wpm"] and abs(audio["speech_rate_wpm"] - 220.0) > 70:
            risks.append("语速波动较大，可能影响信息接收效率。")
        if audio["avg_pause_ratio"] > 0.35:
            risks.append("停顿偏多，表达连续性偏弱。")
        if audio["filler_density"] > 0.03:
            risks.append("口头禅较多，影响表达利落度。")
        if video["gaze_aversion_rate"] > 0.45:
            risks.append("视线离开镜头时间偏长，自信感略弱。")
        if video["head_jitter"] > 0.22:
            risks.append("头部动作较多，肢体稳定性偏弱。")
        if not video["window_count"]:
            risks.append("缺少视频模态，无法充分评估非语言表达。")
        if not audio["segment_count"]:
            risks.append("缺少音频模态，无法充分评估语速和流利度。")
        if min(dimension_scores.values()) < 55:
            risks.append("部分表达维度低于稳定线，建议人工复核具体片段。")
        return risks

    @staticmethod
    def _build_summary(
        dimension_scores: Dict[str, int],
        confidence_level: str,
        evidence_summary: List[str],
        risk_flags: List[str],
    ) -> str:
        strongest = max(dimension_scores, key=lambda k: dimension_scores[k])
        weakest = min(dimension_scores, key=lambda k: dimension_scores[k])
        summary = (
            f"表达分析显示候选人的优势集中在 {strongest}，"
            f"相对短板在 {weakest}。"
            f"当前报告置信度为 {confidence_level}。"
        )
        if risk_flags:
            summary += f" 主要风险包括：{risk_flags[0]}"
        elif evidence_summary:
            summary += f" 关键证据：{evidence_summary[0]}"
        return summary.strip()


_expression_analyzer_service: Optional[ExpressionAnalyzerService] = None


def init_expression_analyzer_service(settings) -> ExpressionAnalyzerService:
    global _expression_analyzer_service
    _expression_analyzer_service = ExpressionAnalyzerService(settings)
    return _expression_analyzer_service


def get_expression_analyzer_service() -> ExpressionAnalyzerService:
    if _expression_analyzer_service is None:
        raise RuntimeError("Expression analyzer service not initialized")
    return _expression_analyzer_service
