import streamlit as st
import asyncio
from pathlib import Path
import builtins
from test_research_workflow import research_topic
from test_illustrator import generate_illustration
from test_research_to_slides import structure_essay
from test_video import EssayVideo
from manim import config
import shutil
import json

st.set_page_config(
    page_title="3Research1Video",
    page_icon="📝",
    menu_items={
        'About': """
        This app takes a research topic and automatically:
        1. Researches and generates a comprehensive essay
        2. Creates visual elements for the presentation
        3. Structures the content into a video format
        4. Produces a final video presentation
        
        The process may take several minutes depending on the complexity of the topic.
        """
    }
)

st.title("3Research1Video")
st.write("Transform any research topic into an engaging video presentation!")

# Add sidebar with About information
with st.sidebar:
    st.header("About")
    st.write("""
    This app takes a research topic and automatically:
    1. Researches and generates a comprehensive essay
    2. Creates visual elements for the presentation
    3. Structures the content into a video format
    4. Produces a final video presentation
    
    The process may take several minutes depending on the complexity of the topic.
    """)

def main():
    # Input section
    topic = st.text_input("Enter your research topic:", 
                         placeholder="e.g., artificial intelligence in material science")

    if st.button("Generate Video", disabled=not topic):
        # Create status containers
        status_area = st.empty()
        progress_text = ""
        
        def update_status(message):
            nonlocal progress_text
            progress_text += f"{message}\n"
            status_area.code(progress_text)
        
        try:
            with st.spinner("Cooking you something nice..."):
                output_dir = Path("publication")
                output_dir.mkdir(exist_ok=True)

                # Step 1: Research and Essay Generation (async)
                update_status(f"🔍 Starting research on topic: {topic}")
                async def research_and_write():
                    essay = await research_topic(topic)
                    return essay

                essay = asyncio.run(research_and_write())
                update_status("✅ Research complete")

                # Save essay
                essay_path = output_dir / f"{topic.replace(' ', '_').lower()}_essay.md"
                with open(essay_path, 'w', encoding='utf-8') as f:
                    f.write(str(essay))
                update_status("📝 Essay generated and saved")

                # Step 2: Generate illustration
                update_status("🎨 Creating illustration...")
                illustration_path = output_dir / f"{topic.replace(' ', '_').lower()}_illustration.jpg"
                success = generate_illustration(str(essay), str(illustration_path))
                if success:
                    update_status("✅ Illustration created successfully")
                else:
                    update_status("⚠️ Using default illustration")

                # Step 3: Structure essay into slides
                update_status("📏 Structuring content into presentation format...")
                structured_content = structure_essay(str(essay))
                structured_content_path = output_dir / f"{topic.replace(' ', '_').lower()}_structured_content.json"
                with open(structured_content_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_content, f, indent=2)
                update_status("✅ Content structure complete")

                # Step 4: Generate video
                update_status("🎞 Generating video presentation...")
                video_name = f"{topic.replace(' ', '_').lower()}_video"
                final_video_path = output_dir / f"{video_name}.mp4"

                try:
                    # Configure Manim
                    config.media_dir = str(output_dir)
                    config.video_dir = str(output_dir)
                    config.output_file = video_name
                    config.quality = "medium_quality"
                    config.flush_cache = True

                    scene = EssayVideo(structured_content, str(illustration_path))
                    scene.render()
                    update_status("✅ Video generation complete")

                except Exception as e:
                    # Check if video was actually generated despite the error
                    if final_video_path.exists():
                        update_status("✅ Video generated successfully despite some non-critical errors")
                    else:
                        update_status(f"⚠️ Error during video generation: {str(e)}")
                        raise e

                finally:
                    # Clean up temporary directories
                    if Path("media").exists():
                        shutil.rmtree("media")
                    if Path("slides").exists():
                        shutil.rmtree("slides")

                update_status("✨ All processing complete!")

            # Display results in tabs
            tab1, tab2 = st.tabs(["Essay", "Video"])
            
            with tab1:
                st.header("Generated Essay")
                if essay_path.exists():
                    with open(essay_path, 'r') as f:
                        essay_content = f.read()
                        st.markdown(essay_content)
                        st.download_button(
                            label="Download Essay",
                            data=essay_content,
                            file_name=f"{topic.replace(' ', '_').lower()}_essay.md",
                            mime="text/markdown"
                        )
            
            with tab2:
                st.header("Generated Video")
                if final_video_path.exists():
                    with open(final_video_path, 'rb') as f:
                        video_data = f.read()
                        st.video(video_data)
                        st.download_button(
                            label="Download Video",
                            data=video_data,
                            file_name=f"{topic.replace(' ', '_').lower()}_video.mp4",
                            mime="video/mp4"
                        )
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 