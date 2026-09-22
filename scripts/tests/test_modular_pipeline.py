from diffusers.modular_pipelines import MiniMaxH3ModularPipeline
import torch

print("MiniMaxH3ModularPipeline found!")

# Load the pipeline
pipe = MiniMaxH3ModularPipeline.from_pretrained(
    "/home/huntingvision/models/minimax-h3/FL2VA",
    trust_remote_code=True,
    torch_dtype=torch.bfloat16
)
print(f"Loaded: {type(pipe)}")
print(f"Device: {pipe.device}")

# Check available components
if hasattr(pipe, 'components'):
    print("Components:", list(pipe.components.keys()))
if hasattr(pipe, 'config'):
    print("Config keys:", list(pipe.config.keys()))

# Try a simple generation
prompt = "A cute cat playing with a ball of yarn in a sunny living room, 4K quality, cinematic lighting"

try:
    output = pipe(
        prompt=prompt,
        width=512,
        height=288,
        fps=8,
        num_inference_steps=5,
        flow_shift=12,
        seed=42,
        duration=2.0,
        task="t2va"
    )
    print(f"Generation successful! Output type: {type(output)}")
    if hasattr(output, 'frames'):
        print(f"Frames shape: {output.frames.shape}")
except Exception as e:
    print(f"Generation error: {e}")
    import traceback
    traceback.print_exc()