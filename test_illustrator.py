import os
from llama_index.llms.azure_openai import AzureOpenAI 
from llama_index.llms.openai import OpenAI
from openai import OpenAI as oai
import requests
from dotenv import load_dotenv


load_dotenv()

# Set up Azure OpenAI environment variables
os.environ["OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_KEY")
os.environ["AZURE_OPENAI_ENDPOINT"] = os.getenv("AZURE_OPENAI_ENDPOINT")
os.environ["OPENAI_API_VERSION"] = os.getenv("AZURE_OPENAI_API_VERSION")

def download_image(url, save_path):
    """Download an image from a URL and save it to disk"""
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print('Illustration successfully downloaded and saved')
        return True
    else:
        print('Failed to download illustration')
        return False

def generate_illustration(story_text, output_path="story_illustration.jpg"):
    """Generate an illustration for a given story text using DALL-E"""
    # First, generate the prompt using GPT-4
    llm = AzureOpenAI(
        engine="gpt-4o-mini",
        model="gpt-4o-mini",
        temperature=0.7
    )
    
    prompt_response = llm.complete(f'''You are a veteran illustration artist for long form articles. 
                                   Here is an article: {story_text}. Think of concept for an anime style illustration for this article 
                                   and write a prompt for DALL-E-3 to draw it. Your prompt:''')
    
    draw_prompt = str(prompt_response)
    print(f"Generated prompt: {draw_prompt}")
    
    # Generate the image using DALL-E
    client = oai(api_key=os.getenv("OPENAI_API_KEY_REGULAR"))
    response = client.images.generate(
        model="dall-e-3",
        prompt=draw_prompt,
        size="1024x1024",
        quality="standard",
        n=1
    )

    image_url = response.data[0].url
    print(f"Generated image URL: {image_url}")
    
    # Download and save the image
    return download_image(image_url, output_path)

def main():
    
    
    # Read the story text
    try:
        with open('test_essay.md', 'r', encoding='utf-8') as f:
            story_text = f.read()
    except FileNotFoundError:
        print("Error: Could not find story file. Please ensure 'test_essay.md' exists.")
        return
    
    # Generate and save the illustration
    output_path = "test_essay_illustration.jpg"
    success = generate_illustration(story_text, output_path)
    
    if success:
        print(f"Illustration has been generated and saved to {output_path}")
    else:
        print("Failed to generate illustration")

if __name__ == "__main__":
    main()