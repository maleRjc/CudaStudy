"""
Visual design tokens for CUDA educational animations.

Tuned for high contrast on dark displays: white primary text, light secondary
text (never near-black), saturated accents, and panels that separate from the
background without looking muddy.
"""

# Brand & Identity Colors
NVIDIA_GREEN = "#76B900"
BG_DARK = "#05080D"
CARD_BG = "#0E1621"
CARD_BORDER = "#2C3E50"

# Semantic State Colors
THREAD_DEFAULT = "#22D3EE"       # Bright cyan (normal active thread)
THREAD_IDLE = "#64748B"          # Slate (inactive / masked out)
THREAD_CONFLICT = "#FF5D73"      # Red (collision / race condition)
THREAD_RESOLVED = "#A3E635"      # Lime (correct mapping)

WARP_COLOR_A = "#FBBF24"         # Amber (branch A)
WARP_COLOR_B = "#F472B6"         # Pink (branch B / divergent)

MEMORY_BG = "#14202E"            # Memory cell background
MEMORY_BORDER = "#46586D"        # Memory cell border
MEMORY_ACCESSED = "#FBBF24"      # Yellow access flash

TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B6C6D8"
TEXT_CODE = "#7DD3FC"

# Screen Layout Zones (Manim standard camera: 14.22 x 7.02)
ZONE_TOP_Y = 2.8
ZONE_CENTER_Y = 0.3
ZONE_BOTTOM_Y = -1.8

# Standard Font & Text Sizes
FONT_TITLE_SIZE = 38
FONT_SUBTITLE_SIZE = 24
FONT_CODE_SIZE = 22
FONT_BADGE_SIZE = 18
