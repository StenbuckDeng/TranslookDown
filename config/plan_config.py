# config/plan_config.py
"""
功能门控配置 — 所有分层规则集中在这里
修改限制只需改这个文件
"""

PLAN_LIMITS = {
    "free": {
        "max_quality": "720p",
        "max_concurrent": 3,
        "max_batch": 10,
        "allowed_platforms": [
            "bilibili", "douyin", "youtube",
            "twitter", "instagram", "x.com",
        ],
        "subtitles": False,
        "metadata": False,
        "thumbnail": False,
        "watermark": True,
    },
    "pro": {
        "max_quality": "4K",
        "max_concurrent": 10,
        "max_batch": 999,
        "allowed_platforms": ["*"],
        "subtitles": True,
        "metadata": True,
        "thumbnail": True,
        "watermark": False,
    },
    "team": {
        "max_quality": "8K",
        "max_concurrent": 30,
        "max_batch": 9999,
        "allowed_platforms": ["*"],
        "subtitles": True,
        "metadata": True,
        "thumbnail": True,
        "watermark": False,
        "api_access": True,
        "team_history": True,
    },
}

# 升级引导文案
UPGRADE_MESSAGES = {
    "quality_limit": {
        "title": "需要 Pro 解锁 4K / 1080p 画质",
        "body": "免费版最高支持 720p。升级 Pro 解锁 4K/1080p 及更多平台。",
        "cta": "升级 Pro · $19/年",
    },
    "platform_limit": {
        "title": "此平台需要 Pro",
        "body": "免费版支持 Bilibili、抖音、YouTube、X、Instagram。\nPro 解锁全部 10,000+ 平台。",
        "cta": "升级 Pro · $19/年",
    },
    "concurrent_limit": {
        "title": "并发下载数已达上限",
        "body": "免费版最多同时下载 3 个。Pro 版支持 10 个并发。",
        "cta": "升级 Pro · $19/年",
    },
    "subtitle_limit": {
        "title": "字幕下载需要 Pro",
        "body": "Pro 版支持 50+ 语言字幕下载及元数据保存。",
        "cta": "升级 Pro · $19/年",
    },
    "thumbnail_limit": {
        "title": "缩略图下载需要 Pro",
        "body": "Pro 版支持下载视频缩略图及嵌入封面。",
        "cta": "升级 Pro · $19/年",
    },
    "metadata_limit": {
        "title": "元数据嵌入需要 Pro",
        "body": "Pro 版支持嵌入元数据和章节信息。",
        "cta": "升级 Pro · $19/年",
    },
}

# 画质等级映射（yt-dlp format string → quality tier）
QUALITY_TIER_MAP = {
    "bestvideo+bestaudio/best": "4K",
    "bestvideo[height<=1080]+bestaudio/best[height<=1080]": "1080p",
    "bestvideo[height<=720]+bestaudio/best[height<=720]": "720p",
    "bestaudio": "audio",
}

# 免费版允许的平台关键词（URL 中包含即可）
FREE_PLATFORM_KEYWORDS = [
    "bilibili.com",
    "douyin.com",
    "iesdouyin.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "instagram.com",
]


def get_plan_limit(plan: str, feature: str):
    """获取某个 plan 的某个功能限制"""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).get(feature)


def is_platform_allowed(plan: str, url: str) -> bool:
    """检查 URL 对应的平台是否在当前 plan 允许范围内"""
    allowed = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])["allowed_platforms"]
    if allowed == ["*"]:
        return True
    url_lower = url.lower()
    return any(kw in url_lower for kw in FREE_PLATFORM_KEYWORDS)


def check_feature(plan: str, feature: str) -> bool:
    """检查某功能是否对该 plan 开放（布尔类功能）"""
    return bool(PLAN_LIMITS.get(plan, PLAN_LIMITS["free"]).get(feature, False))


def get_quality_tier(format_string: str) -> str:
    """将 yt-dlp format string 映射到画质等级"""
    return QUALITY_TIER_MAP.get(format_string, "4K")


def is_quality_allowed(plan: str, format_string: str) -> bool:
    """检查所选画质是否在 plan 允许范围内"""
    max_quality = get_plan_limit(plan, "max_quality")
    tier = get_quality_tier(format_string)
    if max_quality == "720p":
        return tier in ("720p", "audio")
    return True  # pro/team 无限制
