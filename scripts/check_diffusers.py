import diffusers
print(diffusers.__version__)
print([x for x in dir(diffusers) if 'MiniMax' in x or 'minimax' in x.lower()])