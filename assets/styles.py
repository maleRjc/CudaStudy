"""
Visual Design Tokens and Layout Standards for CUDA Educational Animations.
"""

# Brand & Identity Colors
NVIDIA_GREEN = "#76B900"
BG_DARK = "#0D1117"
CARD_BG = "#161B22"
CARD_BORDER = "#30363D"

# Semantic State Colors
THREAD_DEFAULT = "#38BDF8"       # Bright Sky Blue (Normal Active Thread)
THREAD_IDLE = "#475569"          # Slate (Inactive / Masked out)
THREAD_CONFLICT = "#EF4444"      # Red-500 (Collision / Race condition)
THREAD_RESOLVED = "#10B981"      # Emerald (Correct Global ID mapping)

WARP_COLOR_A = "#F59E0B"         # Amber (Branch A)
WARP_COLOR_B = "#8B5CF6"         # Violet (Branch B / Divergent)

MEMORY_BG = "#1E293B"            # Memory cell background
MEMORY_BORDER = "#64748B"        # Memory cell border
MEMORY_ACCESSED = "#FBBF24"      # Yellow access flash

TEXT_PRIMARY = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
TEXT_CODE = "#38BDF8"

# Screen Layout Zones (Manim Standard Camera: [-7.11, 7.11] x [-4.0, 4.0])
ZONE_TOP_Y = 2.8
ZONE_CENTER_Y = 0.3
ZONE_BOTTOM_Y = -2.5

# Standard Font & Text Sizes
FONT_TITLE_SIZE = 36
FONT_SUBTITLE_SIZE = 24
FONT_CODE_SIZE = 22
FONT_BADGE_SIZE = 16
