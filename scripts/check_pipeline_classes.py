# Check what's in diffusers for MiniMaxH3
import diffusers
from diffusers.modular_pipelines.minimax_h3.modular_blocks_minimax_h3 import *
import inspect

# List all classes
members = inspect.getmembers(
    __import__('diffusers.modular_pipelines.minimax_h3.modular_blocks_minimax_h3', fromlist=['*']),
    inspect.isclass
)

for name, cls in members:
    if 'MiniMaxH3' in name and 'Pipeline' in name:
        print(f"Pipeline class: {name}")
        print(f"  Module: {cls.__module__}")

# Check if there's a pipeline class
import diffusers.pipelines
print("\nPipeline modules:", [x for x in dir(diffusers.pipelines) if 'minimax' in x.lower()])

# Try to find the pipeline
from diffusers import DiffusionPipeline
print("\nTrying to find pipeline...")
# The pipeline should be registered automatically when the module is imported
try:
    pipe = DiffusionPipeline.from_pretrained("/home/huntingvision/models/minimax-h3/FL2VA", trust_remote_code=True)
    print(f"Loaded: {type(pipe)}")
except Exception as e:
    print(f"Error: {e}")

# Check what's in the modular_pipelines __init__
from diffusers import modular_pipelines
print("\nModular pipelines:", dir(modular_pipelines))