import os
from openai import AzureOpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure Azure OpenAI
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

def structure_essay(essay_content: str) -> dict:
    """Structure the essay into sections using Azure OpenAI."""
    system_prompt = """
    Your task is to analyze the essay and structure it into logical sections. For each section:
    1. Create an appropriate title that reflects the section's content
    2. Provide a concise version of the content suitable for presentation slides
    3. Include the full original content as narration

    Organize the sections in a way that best presents the essay's flow and main arguments.
    The number of sections should be determined by the natural structure of the content.
    The title should be no longer than 3 words.
    There should be no more than 6 sections.
    

    

    Return ONLY a JSON object with this structure:
    {
        "sections": [
            {"title": "Section Title", "text": "Concise slide content", "narration": "Full section content"},
            // ... additional sections as needed
        ]
    }
    DO NOT INCLUDE THE CHARACTER & IN THE NARRATION.
    """
    
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Structure this essay into sections:\n\n{essay_content}"}
        ],
        response_format={ "type": "json_object" }
    )
    
    return json.loads(response.choices[0].message.content)

if __name__ == "__main__":
    # Read the essay file
    with open('test_essay.md', 'r') as f:
        essay_content = f.read()

    # Structure the essay
    structured_content = structure_essay(essay_content)

    # Save the structured content
    with open('structured_slides.json', 'w') as f:
        json.dump(structured_content, f, indent=2)

    print("Structured content saved to structured_slides.json")
    print("\nStructured sections:")
    for section in structured_content["sections"]:
        print(f"\n{section['title']}:")
        print(section['narration'][:100] + "...")
