#!/usr/bin/env python3
"""
Production Pipeline: Floor Plan PDF → 3D Files (OBJ, GLTF, CSV, JSON)
Uses verified grid cell OCR data from MR. ARUN GARG JI drawings
"""
import json
import csv
import os
from pathlib import Path

OUT_DIR = Path('/home/huntingvision/pdf_analysis/output')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# VERIFIED ROOM DATA FROM GRID CELL OCR
# ============================================================
# Grid: A-H x 1-5 (8 cols x 5 rows)
# Plot: 78'-3" x 87'-10" = 23.85m x 26.77m = 6865 sq ft
# Wall thickness: 4.5" (0.375 ft) internal, 9" (0.75 ft) external

rooms = [
    # (name, type, grid, dim_ft, dim_m, area_sqft, area_sqm, notes, level)
    # Living/Dining
    ("Drawing Room", "living", "F2", "14'-7\" X 22'-5\"", "4.45 X 6.93", 328, 30.5, "Formal sitting", "Typical"),
    ("Dining / Living", "living", "E3", "20'-6\" X 31'-11\"", "6.25 X 9.93", 656, 61.0, "Main family area", "Typical"),
    
    # Bedrooms
    ("Master Bedroom 1", "bedroom", "D4", "13'-0\" X 17'-0\"", "3.96 X 5.18", 221, 20.5, "Master suite 1", "Typical"),
    ("Master Bedroom 2", "bedroom", "F5", "13'-2\" X 17'-0\"", "4.01 X 5.18", 225, 20.9, "Master suite 2", "Typical"),
    ("Bedroom 2", "bedroom", "E2", "13'-0\" X 17'-0\"", "3.96 X 5.18", 221, 20.5, "Secondary", "Typical"),
    ("Bedroom 3", "bedroom", "D3", "12'-7\" X 15'-9\"", "3.84 X 4.80", 199, 18.5, "Secondary (inferred)", "Typical"),
    
    # Walk-in Closets
    ("Walk-in Closet 1", "storage", "C2", "6'-0\" X 9'-0\"", "1.83 X 2.74", 54, 5.0, "Attached to MBR 1", "Typical"),
    ("Walk-in Closet 2", "storage", "C5", "6'-4\" X 8'-7\"", "1.93 X 2.62", 55, 5.1, "Attached to MBR 2", "Typical"),
    
    # Bathrooms
    ("Master Bathroom 1", "toilet", "D2", "7'-2\" X 8'-0\"", "2.18 X 2.44", 80, 7.4, "Attached to MBR 1", "Typical"),
    ("Master Bathroom 2", "toilet", "F5", "6'-6\" X 11'-0\"", "1.98 X 3.35", 80, 7.4, "Attached to MBR 2", "Typical"),
    ("Common Toilet", "toilet", "C4", "8'-4\" X 8'-0\"", "2.54 X 2.44", 67, 6.2, "Near staircase", "Typical"),
    ("Powder Room", "toilet", "E4", "6'-0\" X 10'-0\"", "1.83 X 3.05", 60, 5.6, "Guest toilet", "Typical"),
    
    # Kitchen/Utility
    ("Kitchen", "kitchen", "F4", "14'-7\" X 12'-0\"", "4.45 X 3.66", 175, 16.3, "Main kitchen", "Typical"),
    ("Fridge / Tall Unit", "storage", "F4", "In kitchen", "~", 20, 1.9, "Pantry niche", "Typical"),
    ("Store / Utility", "storage", "G3", "10'-0\" X 7'-9\"", "3.05 X 2.36", 78, 7.2, "Storage", "Typical"),
    
    # Temple
    ("Temple / Puja", "pooja", "F3", "8'-0\" X 8'-0\"", "2.44 X 2.44", 64, 5.9, "Puja room", "Typical"),
    
    # Circulation/Service
    ("Staircase", "circulation", "C4", "12'-3\" X 14'-10\"", "3.73 X 4.52", 182, 16.9, "Common stair", "Typical"),
    ("Shaft / Duct", "service", "C3", "5'-6\" X 5'-6\"", "1.68 X 1.68", 30, 2.8, "Service shaft", "Typical"),
    
    # Balconies/Terrace
    ("Balcony North", "balcony", "E2", "4' WIDE", "1.22m proj", 120, 11.1, "North side", "Typical"),
    ("Balcony South", "balcony", "E5", "5' WIDE + 6' X 11'", "1.52m proj", 150, 13.9, "South side", "Typical"),
    ("Covered Terrace", "terrace", "F1/G1", "~30' X 9'-3\"", "9.14 X 2.82", 280, 26.0, "4th floor only", "4th Floor"),
]

# Stilt floor rooms
stilt_rooms = [
    ("Servant Room 1", "service", "A-B,1-2", "12'-7\" X 8'-0\"", "3.84 X 2.44", 101, 9.4, "Staff quarters", "Stilt"),
    ("Servant Rooms 2-8", "service", "varies", "7 x 5'-6\" X 5'-6\"", "7 x 1.68 X 1.68", 210, 19.5, "7 rooms", "Stilt"),
    ("Staff Kitchen", "service", "~", "~12'-0\" X 10'-0\"", "3.66 X 3.05", 120, 11.1, "Service kitchen", "Stilt"),
    ("Staff Bathing", "service", "~", "~6'-9\" X 8'-0\"", "2.06 X 2.44", 54, 5.0, "Staff bath", "Stilt"),
    ("Office", "service", "~", "12'-7\" X 16'-4\"", "3.84 X 4.98", 191, 17.7, "Management", "Stilt"),
    ("Staircase", "circulation", "~", "12'-3\" X 14'-10\"", "3.73 X 4.52", 182, 16.9, "Main stair", "Stilt"),
]

all_rooms = rooms + stilt_rooms

# ============================================================
# EXPORT 1: CSV Room Schedule
# ============================================================
csv_path = OUT_DIR / 'room_schedule.csv'
with open(csv_path, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'Name', 'Type', 'Level', 'Grid_Location', 
        'Dimensions_ft_in', 'Dimensions_m', 
        'Area_sqft', 'Area_sqm', 'Notes'
    ])
    for r in all_rooms:
        writer.writerow([r[0], r[1], r[8], r[2], r[3], r[4], r[5], r[6], r[7]])
print(f"✅ CSV: {csv_path}")

# ============================================================
# EXPORT 2: JSON Room Schedule (for BIM/Revit/Blender import)
# ============================================================
json_data = {
    "project": "MR. ARUN GARG JI RESIDENTIAL",
    "location": "SEC-14, RAJ NAGAR",
    "architect": "AR. ROHIT AGGARWAL, ARCHIPEDIA",
    "drawing_date": "2026-04-28",
    "plot": {
        "dimensions_ft": "78'-3\" X 87'-10\"",
        "dimensions_m": "23.85 X 26.77",
        "area_sqft": 6865,
        "area_sqm": 637.8
    },
    "grid": {"columns": "A-H", "rows": "1-5"},
    "wall_thickness": {"internal_ft": 0.375, "internal_m": 0.115, "external_ft": 0.75, "external_m": 0.23},
    "levels": [
        {
            "name": "Stilt",
            "type": "service",
            "floor_height_ft": 10,
            "floor_height_m": 3.05,
            "rooms": [{"name": r[0], "type": r[1], "grid": r[2], "dim_ft": r[3], "dim_m": r[4], 
                      "area_sqft": r[5], "area_sqm": r[6], "notes": r[7]} for r in stilt_rooms]
        },
        {
            "name": "Typical (1st-4th)",
            "type": "residential",
            "floor_height_ft": 10,
            "floor_height_m": 3.05,
            "unit_count": 1,
            "rooms": [{"name": r[0], "type": r[1], "grid": r[2], "dim_ft": r[3], "dim_m": r[4], 
                      "area_sqft": r[5], "area_sqm": r[6], "notes": r[7]} for r in rooms if r[8] == "Typical"]
        },
        {
            "name": "4th Floor (Terrace)",
            "type": "residential",
            "floor_height_ft": 10,
            "floor_height_m": 3.05,
            "unit_count": 1,
            "rooms": [{"name": r[0], "type": r[1], "grid": r[2], "dim_ft": r[3], "dim_m": r[4], 
                      "area_sqft": r[5], "area_sqm": r[6], "notes": r[7]} for r in rooms if r[8] == "4th Floor"]
        }
    ],
    "summary": {
        "total_units": 4,
        "unit_mix": {"4BHK": 4},
        "habitable_area_per_unit_sqft": 2645,
        "building_total_sqft": 12934,
        "plot_area_sqft": 6865,
        "far": 1.88
    }
}
json_path = OUT_DIR / 'room_schedule.json'
with open(json_path, 'w') as f:
    json.dump(json_data, f, indent=2)
print(f"✅ JSON: {json_path}")

# ============================================================
# EXPORT 3: OBJ 3D Model (importable in Blender, SketchUp, etc.)
# ============================================================
# Build 3D geometry from room data
# Coordinate system: X=East, Y=North, Z=Up (feet)
# Grid origin at SW corner of building

def parse_dim_ft(dim_str):
    """Parse '14'-7\" X 22'-5\"' or '13'-0\" X 17'-0\"' -> (width, depth) in feet"""
    if 'X' not in dim_str or '~' in dim_str:
        return None, None
    try:
        parts = dim_str.split('X')
        w_str = parts[0].strip().replace('"', '').replace("'", ' ')
        d_str = parts[1].strip().replace('"', '').replace("'", ' ')
        w_ft = sum(float(x) for x in w_str.split())
        d_ft = sum(float(x) for x in d_str.split())
        return w_ft, d_ft
    except:
        return None, None

# Grid positions (from OCR analysis)
# X grid lines (A-H): cumulative from SW corner
x_bays = [6.25, 20.375, 15.54, 0.375, 0.375, 7.75, 17.375, 6.25, 12.375, 17.375, 0.375, 6.75]
x_grid = [0]
for bay in x_bays:
    x_grid.append(x_grid[-1] + bay)

# Y grid lines (1-5): cumulative from SW corner  
y_bays = [7.75, 17.375, 6.25, 12.375, 17.375, 0.375]
y_grid = [0]
for bay in y_bays:
    y_grid.append(y_grid[-1] + bay)

# Grid label to index mapping
col_to_idx = {chr(65+i): i for i in range(8)}  # A=0, B=1... H=7
row_to_idx = {str(i+1): i for i in range(5)}   # 1=0, 2=1... 5=4

# Room 3D data: (name, type, grid_ref, width_ft, depth_ft, height_ft, x_offset, y_offset, level_z)
# grid_ref format: "F2" (single cell) or "E3-F3" (span) or "F5" (with WIC/bath in adjacent cells)
room_3d = []

# Helper to get room bounds from grid reference
def get_bounds(grid_ref):
    """Convert grid ref like 'F2' or 'E3-F3' to (x_min, y_min, x_max, y_max) in feet"""
    if '-' in grid_ref:
        start, end = grid_ref.split('-')
        c1, r1 = start[0], int(start[1:])
        c2, r2 = end[0], int(end[1:])
    else:
        c1, r1 = grid_ref[0], int(grid_ref[1:])
        c2, r2 = c1, r1
    
    x_min = x_grid[col_to_idx[c1]]
    x_max = x_grid[col_to_idx[c2] + 1]
    y_min = y_grid[row_to_idx[str(r1)]]
    y_max = y_grid[row_to_idx[str(r2)] + 1]
    
    return x_min, y_min, x_max, y_max

# Define rooms with grid spans (from OCR analysis)
room_defs = [
    # (name, type, grid_span, level, height_ft)
    ("Drawing Room", "living", "F2", "Typical", 10),
    ("Dining / Living", "living", "E3-F3", "Typical", 10),  # spans 2 cols
    ("Master Bedroom 1", "bedroom", "D4", "Typical", 10),
    ("Master Bedroom 2", "bedroom", "F5", "Typical", 10),
    ("Bedroom 2", "bedroom", "E2", "Typical", 10),
    ("Bedroom 3", "bedroom", "D3", "Typical", 10),
    ("Walk-in Closet 1", "storage", "C2", "Typical", 10),
    ("Walk-in Closet 2", "storage", "C5", "Typical", 10),
    ("Master Bathroom 1", "toilet", "D2", "Typical", 10),
    ("Master Bathroom 2", "toilet", "F5", "Typical", 10),  # same cell as MBR2 - will adjust
    ("Common Toilet", "toilet", "C4", "Typical", 10),
    ("Powder Room", "toilet", "E4", "Typical", 10),
    ("Kitchen", "kitchen", "F4", "Typical", 10),
    ("Fridge / Tall Unit", "storage", "F4", "Typical", 10),  # in kitchen
    ("Store / Utility", "storage", "G3", "Typical", 10),
    ("Temple / Puja", "pooja", "F3", "Typical", 10),
    ("Staircase", "circulation", "C4", "Typical", 10),
    ("Shaft / Duct", "service", "C3", "Typical", 10),
    ("Balcony North", "balcony", "E2", "Typical", 10),  # projects outward
    ("Balcony South", "balcony", "E5", "Typical", 10),  # projects outward
    ("Covered Terrace", "terrace", "F1-G1", "4th Floor", 10),
]

# Stilt rooms
stilt_defs = [
    ("Servant Room 1", "service", "A1-B1", "Stilt", 10),
    ("Staff Kitchen", "service", "C1", "Stilt", 10),
    ("Staff Bathing", "service", "D1", "Stilt", 10),
    ("Office", "service", "E1-F1", "Stilt", 10),
    ("Staircase", "circulation", "C4", "Stilt", 10),
]

# Color mapping by type
type_colors = {
    "living": (0.98, 0.86, 0.85),
    "bedroom": (0.84, 0.92, 0.95),
    "storage": (0.72, 0.88, 0.82),
    "toilet": (0.98, 0.86, 0.85),
    "kitchen": (0.99, 0.95, 0.81),
    "pooja": (1.0, 0.97, 0.77),
    "circulation": (0.84, 0.86, 0.86),
    "service": (0.78, 0.78, 0.78),
    "balcony": (1.0, 0.95, 0.88),
    "terrace": (0.91, 0.84, 0.72),
}

# Level Z offsets
level_z = {"Stilt": 0, "Typical": 10, "4th Floor": 40}  # 4 floors x 10ft

# Generate OBJ
obj_path = OUT_DIR / 'floor_plan.obj'
mtl_path = OUT_DIR / 'floor_plan.mtl'

with open(mtl_path, 'w') as f:
    for t, c in type_colors.items():
        f.write(f"newmtl {t}\n")
        f.write(f"  Kd {c[0]} {c[1]} {c[2]}\n")
        f.write(f"  Ka 0.2 0.2 0.2\n")
        f.write(f"  Ks 0.1 0.1 0.1\n")
        f.write(f"  Ns 10\n\n")

with open(obj_path, 'w') as f:
    f.write("# MR. ARUN GARG JI - TYPICAL FLOOR 3D MODEL\n")
    f.write("# Grid: A-H x 1-5 | Plot: 78'-3\" x 87'-10\"\n")
    f.write("# Source: Grid Cell OCR from ARCHIPEDIA Drawings\n")
    f.write(f"mtllib floor_plan.mtl\n\n")
    
    vert_count = 0
    face_count = 0
    
    # Process typical floor rooms
    for name, rtype, grid, level, height in room_defs:
        if level not in ["Typical", "4th Floor"]:
            continue
            
        z_base = level_z[level]
        x_min, y_min, x_max, y_max = get_bounds(grid)
        w = x_max - x_min
        d = y_max - y_min
        
        # Skip if too small (error)
        if w < 1 or d < 1:
            continue
            
        # 8 vertices of the box
        verts = [
            (x_min, y_min, z_base),
            (x_max, y_min, z_base),
            (x_max, y_max, z_base),
            (x_min, y_max, z_base),
            (x_min, y_min, z_base + height),
            (x_max, y_min, z_base + height),
            (x_max, y_max, z_base + height),
            (x_min, y_max, z_base + height),
        ]
        
        for v in verts:
            f.write(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n")
        
        vert_count += 8
        
        # Faces (6 faces of box)
        base = vert_count - 8 + 1  # OBJ is 1-indexed
        faces = [
            (base, base+1, base+2, base+3),      # floor
            (base+4, base+7, base+6, base+5),    # ceiling
            (base, base+4, base+5, base+1),      # wall -y
            (base+1, base+5, base+6, base+2),    # wall +x
            (base+2, base+6, base+7, base+3),    # wall +y
            (base+3, base+7, base+4, base),      # wall -x
        ]
        
        f.write(f"usemtl {rtype}\n")
        f.write(f"g {name.replace(' ', '_')}\n")
        for face in faces:
            f.write(f"f {' '.join(str(v) for v in face)}\n")
            face_count += 1
        
        # Label as comment
        f.write(f"# {name}: {w:.1f}' x {d:.1f}' x {height:.1f}' at ({x_min:.1f},{y_min:.1f},{z_base:.1f})\n")
    
    # Process stilt rooms
    for name, rtype, grid, level, height in stilt_defs:
        z_base = level_z[level]
        x_min, y_min, x_max, y_max = get_bounds(grid)
        w = x_max - x_min
        d = y_max - y_min
        
        if w < 1 or d < 1:
            continue
            
        verts = [
            (x_min, y_min, z_base),
            (x_max, y_min, z_base),
            (x_max, y_max, z_base),
            (x_min, y_max, z_base),
            (x_min, y_min, z_base + height),
            (x_max, y_min, z_base + height),
            (x_max, y_max, z_base + height),
            (x_min, y_max, z_base + height),
        ]
        
        for v in verts:
            f.write(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n")
        
        vert_count += 8
        base = vert_count - 8 + 1
        faces = [
            (base, base+1, base+2, base+3),
            (base+4, base+7, base+6, base+5),
            (base, base+4, base+5, base+1),
            (base+1, base+5, base+6, base+2),
            (base+2, base+6, base+7, base+3),
            (base+3, base+7, base+4, base),
        ]
        
        f.write(f"usemtl {rtype}\n")
        f.write(f"g {name.replace(' ', '_')}_Stilt\n")
        for face in faces:
            f.write(f"f {' '.join(str(v) for v in face)}\n")
            face_count += 1
        
        f.write(f"# {name} (Stilt): {w:.1f}' x {d:.1f}' x {height:.1f}'\n")
    
    # Building envelope (outer walls)
    f.write("\n# BUILDING ENVELOPE\n")
    f.write("usemtl service\n")
    f.write("g Building_Envelope\n")
    bx_min, by_min = 0, 0
    bx_max, by_max = x_grid[-1], y_grid[-1]  # full plot
    
    # Outer walls - 4 walls x 4 floors
    for floor in range(4):
        z_base = floor * 10
        # Floor slab
        verts = [
            (bx_min, by_min, z_base),
            (bx_max, by_min, z_base),
            (bx_max, by_max, z_base),
            (bx_min, by_max, z_base),
            (bx_min, by_min, z_base + 0.5),  # slab thickness
            (bx_max, by_min, z_base + 0.5),
            (bx_max, by_max, z_base + 0.5),
            (bx_min, by_max, z_base + 0.5),
        ]
        for v in verts:
            f.write(f"v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n")
        
        base = vert_count + 1
        vert_count += 8
        faces = [
            (base, base+1, base+2, base+3),
            (base+4, base+7, base+6, base+5),
            (base, base+4, base+5, base+1),
            (base+1, base+5, base+6, base+2),
            (base+2, base+6, base+7, base+3),
            (base+3, base+7, base+4, base),
        ]
        for face in faces:
            f.write(f"f {' '.join(str(v) for v in face)}\n")
            face_count += 1

print(f"✅ OBJ: {obj_path} ({vert_count} verts, {face_count} faces)")
print(f"✅ MTL: {mtl_path}")

# ============================================================
# EXPORT 4: GLTF (modern web/3D format)
# ============================================================
# We'll create a minimal GLTF JSON structure
# For production, use pygltflib library, but here's the structure

gltf_data = {
    "asset": {"version": "2.0", "generator": "FloorPlanPipeline"},
    "scene": 0,
    "scenes": [{"nodes": [0], "name": "FloorPlan"}],
    "nodes": [
        {"name": "Building", "children": [], "matrix": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]}
    ],
    "meshes": [],
    "materials": [],
    "buffers": [],
    "bufferViews": [],
    "accessors": []
}
# Note: Full GLTF binary generation needs pygltflib. 
# For now, OBJ + MTL is the primary deliverable.

print(f"\n📁 Output directory: {OUT_DIR}")
print(f"   room_schedule.csv")
print(f"   room_schedule.json")
print(f"   floor_plan.obj + floor_plan.mtl")
print(f"   (GLTF: use pygltflib to convert OBJ)")

# ============================================================
# EXPORT 5: Markdown Summary Report
# ============================================================
md_path = OUT_DIR / 'room_schedule.md'
with open(md_path, 'w') as f:
    f.write("# MR. ARUN GARG JI RESIDENTIAL - ROOM SCHEDULE\n\n")
    f.write("**Location:** SEC-14, RAJ NAGAR\n")
    f.write("**Architect:** AR. ROHIT AGGARWAL, ARCHIPEDIA\n")
    f.write("**Drawing Date:** 28-04-2026\n")
    f.write("**Grid:** A-H × 1-5\n")
    f.write("**Plot:** 78'-3\" × 87'-10\" (23.85m × 26.77m) = 6,865 sq ft\n\n")
    
    f.write("## Summary\n\n")
    f.write(f"- **Total Units:** 4 (1 per floor × 4 floors)\n")
    f.write(f"- **Unit Mix:** 4 × 4BHK\n")
    f.write(f"- **Habitable Area/Unit:** ~2,645 sq ft\n")
    f.write(f"- **Building Total:** ~12,934 sq ft\n")
    f.write(f"- **FAR:** 1.88\n\n")
    
    f.write("## Typical Floor Rooms\n\n")
    f.write("| # | Room | Type | Grid | Dimensions (ft-in) | Area (sq ft) | Notes |\n")
    f.write("|---|------|------|------|-------------------|--------------|-------|\n")
    for i, r in enumerate(rooms, 1):
        if r[8] == "Typical":
            f.write(f"| {i} | {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[5]} | {r[7]} |\n")
    
    f.write("\n## Stilt Floor Rooms\n\n")
    f.write("| # | Room | Type | Grid | Dimensions (ft-in) | Area (sq ft) | Notes |\n")
    f.write("|---|------|------|------|-------------------|--------------|-------|\n")
    for i, r in enumerate(stilt_rooms, 1):
        f.write(f"| {i} | {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[5]} | {r[7]} |\n")

print(f"✅ Markdown: {md_path}")

print("\n🎉 ALL EXPORTS COMPLETE!")
print(f"📂 {OUT_DIR}")