"""Byte and structural budgets shared by JSON payloads and framed results."""

JSON_LIMIT = 1_048_576
FRAME_LIMIT = JSON_LIMIT + 1_024
JSON_DEPTH = 32
JSON_NODES = 65_536
