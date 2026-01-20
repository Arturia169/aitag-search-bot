"""AI generation parameter parser and explainer."""

import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# Parameter explanations in Chinese
PARAM_EXPLANATIONS = {
    "steps": {
        "name": "迭代步数 (Steps)",
        "desc": "生成过程的迭代次数。步数越高，细节越丰富，但生成时间也越长。通常 20-30 步就能获得不错的效果。"
    },
    "sampler": {
        "name": "采样器 (Sampler)",
        "desc": "控制图像生成算法的核心组件。不同采样器会产生不同风格的画面。常见的有 Euler、DPM++、DDIM 等。"
    },
    "cfg scale": {
        "name": "提示词引导强度 (CFG Scale)",
        "desc": "决定 AI 对你输入的提示词的遵循程度。数值越高越"听话"但可能过度饱和；越低则更"创意"但可能偏离主题。推荐 5-12。"
    },
    "seed": {
        "name": "随机种子 (Seed)",
        "desc": "决定画面随机性的魔法数字。相同的种子 + 相同的参数 = 相同的画面。用于复现或微调作品。"
    },
    "size": {
        "name": "尺寸 (Size)",
        "desc": "输出图像的分辨率 (宽×高)。常见比例有 1:1 (头像)、16:9 (壁纸)、2:3 (人像) 等。"
    },
    "model": {
        "name": "模型 (Model)",
        "desc": "AI 绘画的"大脑"。不同模型擅长不同风格，如写实、动漫、插画等。这是影响画面风格的最关键因素。"
    },
    "model hash": {
        "name": "模型哈希 (Model Hash)",
        "desc": "模型文件的唯一标识符，用于精确匹配特定版本的模型。"
    },
    "clip skip": {
        "name": "CLIP 层跳过 (Clip Skip)",
        "desc": "跳过 CLIP 文本编码器的后几层。数值越大，对提示词的理解越"抽象"，常用于动漫风格。"
    },
    "denoising strength": {
        "name": "降噪强度 (Denoising)",
        "desc": "图生图 (img2img) 专属参数。数值越高改动越大，越低则越接近原图。"
    },
    "schedule type": {
        "name": "调度类型 (Schedule)",
        "desc": "控制采样过程中噪声去除的节奏。不同调度器会影响最终画面的质感。"
    },
    "vae": {
        "name": "VAE 模型",
        "desc": "变分自编码器，负责图像的编解码。不同 VAE 会影响颜色饱和度和细节表现。"
    },
    "lora": {
        "name": "LoRA 微调模型",
        "desc": "轻量级微调模型，用于添加特定角色、风格或概念，无需替换主模型。"
    }
}


def parse_parameters(prompt_text: str) -> Dict[str, str]:
    """Parse generation parameters from prompt text.
    
    Args:
        prompt_text: Raw prompt text containing parameters
        
    Returns:
        Dictionary of parameter name -> value
    """
    if not prompt_text:
        return {}
    
    params = {}
    
    # Common patterns: "Key: Value" or "Key:Value"
    # Example: "Steps: 20, Sampler: Euler, CFG scale: 7, Seed: 12345"
    patterns = [
        # Standard format: Key: Value
        r'(Steps|Sampler|CFG scale|Seed|Size|Model|Model hash|Clip skip|Denoising strength|Schedule type|VAE)\s*[:：]\s*([^,\n]+)',
        # LoRA detection
        r'<lora:([^:>]+):[^>]+>',
    ]
    
    for pattern in patterns[:1]:  # First pattern for standard params
        matches = re.findall(pattern, prompt_text, re.IGNORECASE)
        for key, value in matches:
            params[key.lower().strip()] = value.strip().rstrip(',')
    
    # LoRA detection
    lora_matches = re.findall(patterns[1], prompt_text, re.IGNORECASE)
    if lora_matches:
        params["lora"] = ", ".join(lora_matches)
    
    return params


def explain_parameters(params: Dict[str, str]) -> str:
    """Generate a formatted explanation of parameters.
    
    Args:
        params: Dictionary of parameter name -> value
        
    Returns:
        Formatted HTML string with explanations
    """
    if not params:
        return "😕 未能从该作品中识别到生成参数。"
    
    lines = ["🎨 <b>AI 生成参数解读</b>\n"]
    
    for key, value in params.items():
        key_lower = key.lower()
        if key_lower in PARAM_EXPLANATIONS:
            info = PARAM_EXPLANATIONS[key_lower]
            lines.append(f"<b>📌 {info['name']}</b>")
            lines.append(f"   值：<code>{value}</code>")
            lines.append(f"   💡 {info['desc']}\n")
        else:
            # Unknown parameter, just show the value
            lines.append(f"<b>📌 {key}</b>: <code>{value}</code>\n")
    
    return "\n".join(lines)


def get_quick_summary(params: Dict[str, str]) -> str:
    """Get a one-line summary of key parameters.
    
    Args:
        params: Dictionary of parameter name -> value
        
    Returns:
        Short summary string
    """
    parts = []
    
    if "model" in params:
        # Extract just the model name without hash
        model_name = params["model"].split(",")[0].strip()
        parts.append(f"🤖 {model_name}")
    
    if "steps" in params:
        parts.append(f"🔄 {params['steps']}步")
    
    if "cfg scale" in params:
        parts.append(f"📊 CFG {params['cfg scale']}")
    
    if "sampler" in params:
        sampler = params["sampler"].split()[0]  # Just first word
        parts.append(f"🎯 {sampler}")
    
    return " | ".join(parts) if parts else ""
