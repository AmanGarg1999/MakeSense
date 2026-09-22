"""Parser for LLM script generation output."""

import re
from typing import List, Optional
from ..models.output_models import (
    Hook, RetentionBeat, CTA, TitleIdeas, ThumbnailIdeas,
    ScriptVariant, FrameworkType
)
from ..models.input_models import Topic


def parse_hook(text: str) -> Hook:
    """Parse hook from LLM output."""
    hook_text = ""
    technique = "pattern_interrupt"
    retention_impact = 0.7
    
    # Extract hook text
    hook_match = re.search(r'Text:\s*(.+)', text)
    if hook_match:
        hook_text = hook_match.group(1).strip()
    
    # Extract technique
    tech_match = re.search(r'Technique:\s*(.+)', text)
    if tech_match:
        technique = tech_match.group(1).strip().lower()
    
    # Extract retention impact
    impact_match = re.search(r'Retention Impact:\s*([\d.]+)', text)
    if impact_match:
        retention_impact = float(impact_match.group(1))
    
    return Hook(
        text=hook_text,
        framework=FrameworkType.AIDA,  # Will be overridden
        technique=technique,
        estimated_retention_impact=retention_impact
    )


def parse_beats(text: str) -> List[RetentionBeat]:
    """Parse retention beats from LLM output."""
    beats = []
    
    # Pattern: [Timestamp] | [Content] | [Purpose] | [Visual Cue]
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('==='):
            continue
        
        # Try pipe-separated format
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            timestamp = parts[0].strip('[] ')
            content = parts[1]
            purpose = parts[2].replace('Purpose:', '').strip()
            visual_cue = parts[3] if len(parts) > 3 else None
            
            beats.append(RetentionBeat(
                timestamp_range=timestamp,
                content=content,
                purpose=purpose,
                visual_cue=visual_cue
            ))
    
    return beats


def parse_cta(text: str) -> CTA:
    """Parse CTA from LLM output."""
    primary = ""
    secondary = None
    placement = "end"
    style = "direct"
    
    primary_match = re.search(r'Primary:\s*(.+)', text)
    if primary_match:
        primary = primary_match.group(1).strip()
    
    secondary_match = re.search(r'Secondary:\s*(.+)', text)
    if secondary_match:
        sec = secondary_match.group(1).strip()
        if sec.lower() not in ['none', 'n/a', '']:
            secondary = sec
    
    placement_match = re.search(r'Placement:\s*(.+)', text)
    if placement_match:
        placement = placement_match.group(1).strip().lower()
    
    style_match = re.search(r'Style:\s*(.+)', text)
    if style_match:
        style = style_match.group(1).strip().lower()
    
    return CTA(
        primary=primary,
        secondary=secondary,
        placement=placement,
        style=style
    )


def parse_titles(text: str) -> TitleIdeas:
    """Parse titles and thumbnail concepts from LLM output."""
    titles = []
    predicted_ctr = []
    thumbnail_concepts = []
    
    lines = text.strip().split('\n')
    in_thumbnails = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if 'THUMBNAIL' in line.upper():
            in_thumbnails = True
            continue
        
        if in_thumbnails:
            # Thumbnail concepts
            match = re.match(r'\d+\.\s*(.+)', line)
            if match:
                thumbnail_concepts.append(match.group(1).strip())
        else:
            # Titles with CTR
            match = re.match(r'\d+\.\s*(.+?)\s*\|\s*Pred\. CTR:\s*([\d.]+)', line)
            if match:
                titles.append(match.group(1).strip())
                predicted_ctr.append(float(match.group(2)))
            else:
                # Fallback: just numbered titles
                match = re.match(r'\d+\.\s*(.+)', line)
                if match and '|' not in line:
                    titles.append(match.group(1).strip())
                    predicted_ctr.append(0.05)  # Default
    
    return TitleIdeas(
        titles=titles,
        thumbnail_concepts=thumbnail_concepts,
        predicted_ctr=predicted_ctr
    )


def parse_full_script(text: str) -> str:
    """Extract full script from LLM output."""
    # Find the FULL SCRIPT section
    match = re.search(r'=== FULL SCRIPT ===\s*(.+)', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_generation_output(
    raw_output: str,
    framework: FrameworkType,
    topic: Topic,
    target_duration: int = 90
) -> ScriptVariant:
    """Parse complete LLM output into a ScriptVariant."""
    
    # Extract sections
    hook_text = extract_section(raw_output, "HOOK")
    beats_text = extract_section(raw_output, "BEATS")
    cta_text = extract_section(raw_output, "CTA")
    titles_text = extract_section(raw_output, "TITLES")
    full_script = parse_full_script(raw_output)
    
    # Parse each section
    hook = parse_hook(hook_text)
    hook.framework = framework
    
    beats = parse_beats(beats_text)
    
    cta = parse_cta(cta_text)
    
    title_ideas = parse_titles(titles_text)
    
    # Estimate word count and duration
    word_count = len(full_script.split())
    estimated_duration = max(target_duration, word_count // 3)  # ~3 words/second spoken
    
    return ScriptVariant(
        framework=framework,
        hook=hook,
        beats=beats,
        cta=cta,
        title_ideas=title_ideas,
        full_script=full_script,
        estimated_duration_seconds=estimated_duration,
        word_count=word_count
    )


def extract_section(text: str, section_name: str) -> str:
    """Extract a section between === SECTION === markers."""
    pattern = rf'=== {section_name} ===\s*(.*?)(?=== \w+ ===|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""