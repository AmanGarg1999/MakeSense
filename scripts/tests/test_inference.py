import torch
from diffusers import MiniMaxH3ModularPipeline
import os

# Set the model path
model_path = "/home/huntingvision/models/minimax-h3/FL2VA"

print(f"Loading MiniMax-H3 Modular Pipeline from {model_path}")

try:
    # Try loading the modular pipeline
    pipe = MiniMaxH3ModularPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    print("Pipeline loaded successfully!")
    print(f"Pipeline components: {pipe.components}")
    
    # Try a simple inference
    prompt = "A beautiful sunset over a calm ocean, cinematic lighting"
    print(f"Generating video with prompt: {prompt}")
    
    video = pipe(
        prompt=prompt,
        width=1024,
        height=576,
        num_frames=16,
        num_inference_steps=15,
        generator=torch.Generator(device="cuda").manual_seed(42)
    ).frames[0]
    
    # Save the video
    output_path = "/home/huntingvision/generated_video.mp4"
    # Convert frames to video
    from diffusers.utils import export_to_video
    export_to_video(video, output_path, fps=24)
    print(f"Video saved to {output_path}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()