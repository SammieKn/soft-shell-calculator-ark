from soft_shell_calculator_lib.models.retaining_wall import RetainingWall
from pathlib import Path

wall = RetainingWall.from_directory(Path("data/IML metingen NHG0302"))

print("test")
