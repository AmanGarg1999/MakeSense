#!/usr/bin/env python3
"""
Test loading minimax-H3 model from local weights on DGX Spark
"""
import torch
from diffusers import DiffusionPipeline

print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA device:", torch.cuda.get_device_name(0))
    print("CUDA version:", torch.version.cuda)

model_path = "/home/huntingvision/models/minimax-h3/FL2VA/"

try:
    print(f"Loading minimax-H3 from {model_path}...")
    pipe = DiffusionPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        local_files_only=True
    )
    print("Pipeline loaded successfully!")
    print("Pipeline components:", pipe.components.keys())
    
    # Move to GPU if available
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
        print("Pipeline moved to CUDA")
    
    # Test generation
    print("Running test generation...")
    prompt = "A beautiful sunset over mountains, cinematic lighting"
    result = pipe(prompt=prompt, num_frames=16, height=512, width=512, num_inference_steps=10)
    
    print("Generation complete!")
    print("Result type:", type(result))
    if hasattr(result, 'frames'):
        print("Frames shape:", result.frames[0].shape if result.frames else "None")
    elif hasattr(result, 'videos'):
        print("Videos shape:", result.videos[0].shape if result.videos else "None")
    else:
        print("Result attributes:", dir(result))
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()