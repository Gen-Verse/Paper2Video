
import subprocess
import os
from pymol import cmd
import tempfile


def generate_mol_animation(pdb_file: str, output_mp4: str) -> None:
    cmd.reinitialize()
    cmd.load(pdb_file)
    cmd.bg_color("white")
    cmd.color("marine", "all")

    # choosable
    cmd.hide("everything")   # 
    cmd.show("sticks")       # 
    cmd.show("spheres", "elem C")  # choosable
    # finish

    cmd.zoom("all", 2)
    frames = 60
    cmd.mset(f"1-{frames}")
    temp_dir = tempfile.mkdtemp(prefix="pymol_")

    for i in range(1, frames + 1):
        cmd.frame(i)
        angle = (i - 1) * 180 / frames
        cmd.turn("y", angle)
        cmd.png(os.path.join(temp_dir, f"frame{i:04d}.png"),
                width=1280, height=720, dpi=150, ray=0)
    cmd.reinitialize()
    if subprocess.run(["ffmpeg", "-version"],
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode == 0:
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "12",
            "-i", os.path.join(temp_dir, "frame%04d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_mp4
        ], check=True)
        print(f"Complete → {output_mp4}")
    else:
        print("ffmpeg not found")

# # 
# generate_mol_animation(
#     r"C:\Users\Stan\Desktop\AgenticIR-main\dataset\9ngi.pdb",
#     r"C:\Users\Stan\Desktop\AgenticIR-main\dataset\1.mp4"

# )
