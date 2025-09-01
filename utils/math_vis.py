from manim import *
from pydub import AudioSegment
import textwrap
from moviepy.editor import VideoFileClip
class Math_visual(Scene):
    def __init__(self, plan=None):
        super().__init__()
        self.plan = plan
    def construct(self):
        # Title for the formula
        if "scenario" in self.plan:
            title = Text(self.plan["scenario"], font_size=36).to_edge(UP)
            self.play(FadeIn(title))

        col_width   = config.frame_width / 3
        col_center  = RIGHT * (config.frame_width / 3)

        wrapped_lines = textwrap.fill(self.plan["audio_content"], width=20).splitlines()

        ruler = Text("A"*20, font_size=80)
        for font in range(80, 9, -2):
            ruler.font_size = font
            if ruler.width <= col_width - 0.4:
                break
        optimal_font = font

        paragraph = Paragraph(
            *wrapped_lines,           
            font_size=optimal_font,
            line_spacing=1.3,
            alignment="center"
        )

        paragraph.move_to(col_center)

        self.play(FadeIn(paragraph))
    
        self.animate()

    def animate(self):
    # Title text explaining the two major classes of simulation methods
        # title = Text("Two Major Classes of Simulation Methods", font_size=24).to_edge(UP)
    
    # Create two main boxes representing the two classes
        left_box = Rectangle(width=3, height=4, color=BLUE).to_edge(LEFT, buff=1)
        right_box = Rectangle(width=3, height=4, color=GREEN).to_edge(RIGHT, buff=1)
    
    # Labels for each box
        left_label = Text("Multipole summary", font_size=18).next_to(left_box, UP)
        right_label = Text("External influence", font_size=18).next_to(right_box, UP)

        self.play(
            Create(left_box),
            Create(right_box),
            Write(left_label),
            Write(right_label)
        )
        self.wait(2)
    
    # Particle method visualization (left box)
        particles = VGroup(*[Dot(radius=0.05, color=RED) for _ in range(20)])
        particles.arrange_in_grid(4, 5, buff=0.2).move_to(left_box)
        particle_arrows = VGroup(*[
            Arrow(start=part.get_center(), end=part.get_center()+np.random.uniform(-0.3, 0.3, 3), 
                color=YELLOW, buff=0, max_tip_length_to_length_ratio=0.2)
            for part in particles
        ])
    
        self.play(
            FadeIn(particles),
            LaggedStart(*[GrowArrow(arrow) for arrow in particle_arrows], lag_ratio=0.1)
        )
        self.wait(2)
    
    # Multipole method visualization (right box)
        level1 = VGroup(*[Circle(radius=0.2, color=WHITE) for _ in range(4)])
        level1.arrange_in_grid(2, 2, buff=0.5).move_to(right_box.get_center() + UP*0.5)
    
        level2 = Circle(radius=0.8, color=WHITE).move_to(right_box.get_center() + DOWN*0.5)
    
        merge_lines = VGroup(*[
            Line(start=circle.get_bottom(), end=level2.get_top(), color=WHITE)
            for circle in level1
        ])
    
        self.play(
            FadeIn(level1),
            run_time=1.5
        )
        self.wait(1)
    
        self.play(
            Create(merge_lines),
            Create(level2),
            run_time=2
        )
    
    # Animation showing the two-stage process
        stage1_text = Text("Left: Multipole Compression", font_size=16).next_to(ORIGIN + DOWN*1).shift(LEFT*1.8)
        stage2_text = Text("Second: Far-field Influence", font_size=16).next_to(stage1_text, DOWN)
    
        self.play(Write(stage1_text))
        self.wait(1.5)
        self.play(Write(stage2_text))
        self.wait(3)



# Main rendering function that returns the video
def render_video(dir, plan):
    config.media_dir = dir  # Set media directory
    config.output_file = "scene.mp4"  # Set output file name
    scene = Math_visual(plan)  # Create scene
    scene.render()  # Render the video
    return config.output_file  # Return the generated video file path

    
