from manim import *
from manim_slides import Slide
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.azure import AzureService
import os
from dotenv import load_dotenv
import json
from pathlib import Path
from typing import TypedDict, List

# Load environment variables
load_dotenv()

class Section(TypedDict):
    title: str
    narration: str

class EssayStructure(TypedDict):
    sections: List[Section]

class EssayVideo(VoiceoverScene, Slide):
    def __init__(self, sections_data: EssayStructure, image_path: str, *args, **kwargs):
        self.sections_data = sections_data
        self.image_path = image_path
        super().__init__(*args, **kwargs)

    def find_optimal_font_size(self):
        # Layout parameters for testing
        margin = 0.8
        title_buff = 0.5
        line_spacing = 0.3
        min_font_size = 120  # Significantly increased minimum
        max_font_size = 200  # Significantly increased maximum
        title_font_size = 72

        # Available space calculations for right half of screen
        available_width = (config.frame_width / 2) - 2 * margin
        
        def test_font_size(size):
            # Create a test title to account for its space
            test_title = Text("Test", font_size=title_font_size)
            max_height = config.frame_height - test_title.height - 2 * title_buff - 0.5

            # Test each section's paragraph
            for sec in self.sections_data["sections"]:
                paragraph_text = sec["narration"].strip()
                
                # Create test paragraph
                test_paragraph = Paragraph(
                    paragraph_text,
                    font_size=size,
                    width=available_width,
                    line_spacing=line_spacing,
                    alignment="left"
                )
                
                # Check if it fits
                if test_paragraph.height > max_height:
                    return False
            return True

        # Binary search for the largest working font size
        left, right = min_font_size, max_font_size
        optimal_size = min_font_size
        while left <= right:
            mid = (left + right) // 2
            if test_font_size(mid):
                optimal_size = mid
                left = mid + 1
            else:
                right = mid - 1

        return optimal_size

    def construct(self):
        # Azure TTS setup
        azure_subscription_key = os.getenv("AZURE_SUBSCRIPTION_KEY")
        azure_service_region = os.getenv("AZURE_SERVICE_REGION")
        self.set_speech_service(
            AzureService(api_key=azure_subscription_key, region=azure_service_region)
        )

        # Layout parameters
        margin = 0.8
        title_buff = 0.5
        title_font_size = 42
        line_spacing = 0.3

        # Find the optimal font size that works for all slides
        body_font_size = self.find_optimal_font_size()
        print(f"Selected optimal font size: {body_font_size}")

        # Calculate available width for content (right half of screen)
        available_width = (config.frame_width / 2) - 2 * margin

        # Define screen halves
        left_half_center = -config.frame_width/4
        right_half_center = config.frame_width/4

        # Load the image once
        image = ImageMobject(self.image_path)
        
        # Scale image to fit left half of screen with some margin
        image_target_width = config.frame_width / 2 - margin
        image_scale = image_target_width / image.width
        image.scale(image_scale)
        
        # If image is too tall after scaling width, scale it down further
        if image.height > config.frame_height - margin:
            height_scale = (config.frame_height - margin) / image.height
            image.scale(height_scale)
        
        # Position image on left half
        image.move_to([left_half_center, 0, 0])

        # Create cursor for typing effect
        cursor = Rectangle(
            color=BLACK,  # Changed to white for better visibility
            fill_color=BLACK,
            fill_opacity=0,
            stroke_opacity=0,  # Make the outline transparent too
            height=0.00001,  # Much smaller height
            width=0.00001,  # Much thinner width
        ).set_z_index(5).shift(UP * 0.5)  # Shift cursor up and ensure it appears above text

        for sec in self.sections_data["sections"]:
            title_text = sec["title"]
            paragraph_text = sec["narration"].strip()

            # Clear previous slide
            self.clear()

            # Add image to each slide
            self.add(image)

            # Create title and position it on right half
            title = Text(title_text, font_size=title_font_size)
            title.move_to([right_half_center, config.frame_height/2 - title_buff, 0])
            
            # Animate title with cursor
            self.play(TypeWithCursor(
                title, 
                cursor.copy(), 
                time_per_char=0.05,
                keep_cursor_y=False,  # Allow cursor to move with text height
                buff=0.05,
                cursor_opacity=0  # Make cursor completely transparent
            ))

            # Create paragraph with proper wrapping using optimal font size
            paragraph = Text(
                paragraph_text,
                font_size=body_font_size,
                line_spacing=line_spacing,
            ).set_width(available_width)
            
            # Position paragraph on right half, below title with proper spacing
            paragraph_top = title.get_bottom()[1] - title_buff
            paragraph_center_y = paragraph_top - paragraph.height/2
            paragraph.move_to([right_half_center, paragraph_center_y, 0])
            
            # Animate the paragraph with cursor and add voiceover
            cleaned_narration = paragraph_text.replace("&", "and")
            with self.voiceover(text=cleaned_narration) as tracker:
                # Calculate font size scaling factor (larger font = slower typing)
                font_scale_factor = body_font_size / 120  # baseline at font size 120
                adjusted_duration = tracker.duration * font_scale_factor
                
                self.play(
                    TypeWithCursor(
                        paragraph,
                        cursor.copy(),
                        time_per_char=adjusted_duration / len(cleaned_narration),
                        keep_cursor_y=False,  # Allow cursor to move with text height
                        leave_cursor_on=False,
                        buff=0.05,  # Reduced space between cursor and text
                        cursor_opacity=0  # Make cursor completely transparent
                    ),
                    run_time=tracker.duration
                )
            
            # Pause briefly after narration
            self.wait(1)
            
            # Advance to next slide
            self.next_slide()

if __name__ == "__main__":
    # Load structured JSON
    json_path = Path("structured_two.json")
    data = json.loads(json_path.read_text())
    sections_data = data
    
    # Configure image path
    image_path = "dog_love_man.png"  # You can change this as needed

    # Configure Manim output
    output_dir = Path("output"); output_dir.mkdir(exist_ok=True)
    config.media_dir = str(output_dir)
    config.video_dir = str(output_dir)
    config.output_file = "essay_video"
    config.quality = "medium_quality"
    config.flush_cache = True

    # Render
    scene = EssayVideo(sections_data, image_path)
    scene.render()
