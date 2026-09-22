import torch
from diffusers import AutoencoderKLMiniMaxH3, AutoencoderKLMiniMaxH3Audio, MiniMaxH3Transformer3DModel, MiniMaxH3Scheduler
from transformers import Qwen2TokenizerFast, Qwen3VLProcessor
import os

# Check what components we have
model_path = "/home/huntingvision/models/minimax-h3/FL2VA"

print("Checking available components...")

# Check text_encoder
try:
    from transformers import AutoModel
    text_encoder = AutoModel.from_pretrained(os.path.join(model_path, "text_encoder"))
    print("✓ text_encoder loaded")
except Exception as e:
    print(f"✗ text_encoder failed: {e}")

# Check audio_vae
try:
    audio_vae = AutoencoderKLMiniMaxH3Audio.from_pretrained(os.path.join(model_path, "audio_vae"))
    print("✓ audio_vae loaded")
except Exception as e:
    print(f"✗ audio_vae failed: {e}")

# Check video_vae - we don't have it
try:
    video_vae = AutoencoderKLMiniMaxH3.from_pretrained(os.path.join(model_path, "video_vae"))
    print("✓ video_vae loaded")
except Exception as e:
    print(f"✗ video_vae failed: {e}")

# Check transformer
try:
    transformer = MiniMaxH3Transformer3DModel.from_pretrained(os.path.join(model_path, "transformer"))
    print("✓ transformer loaded")
except Exception as e:
    print(f"✗ transformer failed: {e}")

# Check tokenizer
try:
    tokenizer = Qwen2TokenizerFast.from_pretrained(os.path.join(model_path, "processor"))
    print("✓ tokenizer loaded")
except Exception as e:
    print(f"✗ tokenizer failed: {e}")

# Check processor
try:
    processor = Qwen3VLProcessor.from_pretrained(os.path.join(model_path, "processor"))
    print("✓ processor loaded")
except Exception as e:
    print(f"✗ processor failed: {e}")

# Check scheduler
try:
    scheduler = MiniMaxH3Scheduler.from_pretrained(os.path.join(model_path, "scheduler"))
    print("✓ scheduler loaded")
except Exception as e:
    print(f"✗ scheduler failed: {e}")