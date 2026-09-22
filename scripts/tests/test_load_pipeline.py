from diffusers import ModularPipeline
print("ModularPipeline available")

# Check if MiniMaxH3Pipeline is available
from diffusers import DiffusionPipeline
print("Available pipelines:", [x for x in dir(DiffusionPipeline) if 'minimax' in x.lower() or 'MiniMax' in x])

# Try loading the model
try:
    pipe = ModularPipeline.from_pretrained("/home/huntingvision/models/minimax-h3/FL2VA", trust_remote_code=True)
    print("Pipeline loaded successfully!")
    print("Components:", list(pipe.config.keys()) if hasattr(pipe, 'config') else 'No config')
except Exception as e:
    print(f"Error loading pipeline: {e}")
    import traceback
    traceback.print_exc()