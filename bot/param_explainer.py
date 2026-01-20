"""AI generation parameter parser and explainer."""

import re
import json
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
        "desc": "决定 AI 对你输入的提示词的遵循程度。数值越高越'听话'但可能过度饱和；越低则更'创意'但可能偏离主题。推荐 5-12。"
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
        "desc": "AI 绘画的'大脑'。不同模型擅长不同风格，如写实、动漫、插画等。这是影响画面风格的最关键因素。"
    },
    "checkpoint": {
        "name": "基础模型 (Checkpoint)",
        "desc": "ComfyUI 中的主模型文件。决定画面的整体风格和质量。"
    },
    "model hash": {
        "name": "模型哈希 (Model Hash)",
        "desc": "模型文件的唯一标识符，用于精确匹配特定版本的模型。"
    },
    "clip skip": {
        "name": "CLIP 层跳过 (Clip Skip)",
        "desc": "跳过 CLIP 文本编码器的后几层。数值越大，对提示词的理解越'抽象'，常用于动漫风格。"
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
    },
    "workflow": {
        "name": "工作流类型",
        "desc": "该作品使用的生成工具类型，如 ComfyUI、Stable Diffusion WebUI 等。"
    }
}


def parse_comfyui_workflow(text: str) -> Dict[str, str]:
    """Parse ComfyUI workflow JSON to extract parameters."""
    params = {}
    
    try:
        # Try to find JSON in the text
        # ComfyUI workflows are typically nested JSON objects
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            return params
            
        workflow = json.loads(json_match.group())
        
        # Look for common ComfyUI node types
        loras = []
        
        for node_id, node_data in workflow.items():
            if not isinstance(node_data, dict):
                continue
                
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})
            
            # Checkpoint loaders
            if "Checkpoint" in class_type or "CheckpointLoader" in class_type:
                ckpt_name = inputs.get("ckpt_name", "")
                if ckpt_name:
                    # Clean up the name
                    ckpt_name = ckpt_name.replace(".safetensors", "").replace(".ckpt", "")
                    params["checkpoint"] = ckpt_name
            
            # LoRA loaders
            if "Lora" in class_type or "LoRA" in class_type:
                lora_text = inputs.get("text", "") or inputs.get("lora_name", "")
                if lora_text:
                    # Extract lora name from <lora:name:weight> format
                    lora_match = re.search(r'<lora:([^:>]+)', lora_text)
                    if lora_match:
                        loras.append(lora_match.group(1))
                    elif not lora_text.startswith("<"):
                        loras.append(lora_text.replace(".safetensors", ""))
            
            # KSampler nodes
            if "KSampler" in class_type or "Sampler" in class_type:
                if "steps" in inputs:
                    params["steps"] = str(inputs["steps"])
                if "cfg" in inputs:
                    params["cfg scale"] = str(inputs["cfg"])
                if "sampler_name" in inputs:
                    params["sampler"] = inputs["sampler_name"]
                if "scheduler" in inputs:
                    params["schedule type"] = inputs["scheduler"]
                if "seed" in inputs:
                    params["seed"] = str(inputs["seed"])
            
            # VAE
            if "VAE" in class_type:
                vae_name = inputs.get("vae_name", "")
                if vae_name:
                    params["vae"] = vae_name.replace(".safetensors", "")
        
        if loras:
            params["lora"] = ", ".join(loras)
        
        if params:
            params["workflow"] = "ComfyUI"
            
    except (json.JSONDecodeError, Exception) as e:
        logger.debug(f"Failed to parse ComfyUI workflow: {e}")
    
    return params


def parse_parameters(prompt_text: str) -> Dict[str, str]:
    """Parse generation parameters from prompt text (supports SD and ComfyUI formats)."""
    if not prompt_text:
        return {}
    
    params = {}
    
    # Method 1: Standard SD format - "Key: Value" patterns
    patterns = [
        r'(Steps|Sampler|CFG scale|Seed|Size|Model|Model hash|Clip skip|Denoising strength|Schedule type|VAE)\s*[:：]\s*([^,\n]+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, prompt_text, re.IGNORECASE)
        for key, value in matches:
            params[key.lower().strip()] = value.strip().rstrip(',')
    
    # LoRA detection in standard format
    lora_matches = re.findall(r'<lora:([^:>]+):[^>]+>', prompt_text, re.IGNORECASE)
    if lora_matches:
        params["lora"] = ", ".join(lora_matches)
    
    # Method 2: If no standard params found, try ComfyUI workflow format
    if not params:
        params = parse_comfyui_workflow(prompt_text)
    
    return params


def explain_parameters(params: Dict[str, str]) -> str:
    """Generate a formatted explanation of parameters."""
    if not params:
        return "😕 该作品没有可解读的参数信息。\n\n可能原因：\n• 非标准格式工作流\n• 作者未公开参数\n• 参数已被移除"
    
    lines = ["🎨 <b>AI 生成参数解读</b>\n"]
    
    # Show workflow type first if present
    if "workflow" in params:
        lines.append(f"📦 <b>工具</b>: {params['workflow']}\n")
    
    for key, value in params.items():
        if key == "workflow":
            continue
        key_lower = key.lower()
        if key_lower in PARAM_EXPLANATIONS:
            info = PARAM_EXPLANATIONS[key_lower]
            lines.append(f"<b>📌 {info['name']}</b>")
            lines.append(f"   值：<code>{value}</code>")
            lines.append(f"   💡 {info['desc']}\n")
        else:
            lines.append(f"<b>📌 {key}</b>: <code>{value}</code>\n")
    
    return "\n".join(lines)


def get_quick_summary(params: Dict[str, str]) -> str:
    """Get a one-line summary of key parameters."""
    parts = []
    
    # Check for model (SD) or checkpoint (ComfyUI)
    model_name = params.get("model") or params.get("checkpoint")
    if model_name:
        model_name = model_name.split(",")[0].strip()
        if len(model_name) > 20:
            model_name = model_name[:17] + "..."
        parts.append(f"🤖 {model_name}")
    
    if "steps" in params:
        parts.append(f"🔄 {params['steps']}步")
    
    if "cfg scale" in params:
        parts.append(f"📊 CFG {params['cfg scale']}")
    
    if "sampler" in params:
        sampler = params["sampler"].split()[0]
        parts.append(f"🎯 {sampler}")
    
    if "workflow" in params:
        parts.append(f"📦 {params['workflow']}")
    
    return " | ".join(parts) if parts else ""
