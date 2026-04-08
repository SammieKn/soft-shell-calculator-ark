from soft_shell_calculator_lib.models.retaining_wall import RetainingWall
from pathlib import Path

wall = RetainingWall.from_directory(Path("data/IML DYG0101"))

print("test")
