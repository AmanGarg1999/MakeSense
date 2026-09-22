from huggingface_hub import list_repo_files
files = list_repo_files('MiniMaxAI/MiniMax-H3', revision='42ed227ee7df40d41602854ae760620d6eb651fe')
for f in sorted(files):
    if 'FL2VA/video_vae' in f or 'FL2VA/transformer' in f:
        print(f)