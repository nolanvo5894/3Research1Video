import os
from dotenv import load_dotenv
from tavily import TavilyClient
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context
)
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.llms import ChatMessage
from pydantic import BaseModel
import json
import asyncio
from typing import List, Dict

load_dotenv()

# Set up Azure OpenAI environment variables
os.environ["OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_KEY")
os.environ["AZURE_OPENAI_ENDPOINT"] = os.getenv("AZURE_OPENAI_ENDPOINT")
os.environ["OPENAI_API_VERSION"] = os.getenv("AZURE_OPENAI_API_VERSION")

class SubtopicPackage(Event):
    subtopic: str

class SubtopicSourceMaterialPackage(Event):
    subtopic_source_materials: str
    urls: List[str]
    
class SourceMaterialPackage(Event):
    source_materials: str
    all_urls: List[str]

class DraftStoryPackage(Event):
    draft_story: str
    reference_urls: List[str]

class EditorCommentaryPackage(Event):
    editor_commentary: str
    
class FinalStoryPackage(Event):
    final_story: str

class ContentSubtopics(BaseModel):
    """List of subtopics for deeper research on a topic"""
    subtopic_one: str
    subtopic_two: str
    subtopic_three: str

class ResearchWorkflow(Workflow):
    @step
    async def research_source_materials(self, ctx: Context, ev: StartEvent) -> SubtopicPackage: 
        topic = ev.query
        print(f'topic: {topic}')
        await ctx.set('topic', topic)

        tavily_client = TavilyClient()
        response = tavily_client.search(topic)
        source_materials = '\n'.join(result['content'] for result in response['results'])
        
        # Store initial URLs
        initial_urls = [result['url'] for result in response['results']]
        await ctx.set('initial_urls', initial_urls)

        llm = AzureOpenAI(
            engine="o3-mini",
            model="o3-mini",
            temperature=0.3
        )
        sllm = llm.as_structured_llm(output_cls=ContentSubtopics)
        input_msg = ChatMessage.from_str(f'''Generate a list of 3 searchable subtopics to be passed into a search engine for deeper research based on these info about the topic '{topic}': {source_materials}
                                            The subtopics should be closely related to the topic but not overlap and together provide a comprehensive research of the topic.
                                            The subtopics should not be longer than 10 words''')
        response = sllm.chat([input_msg])
        
        subtopics = json.loads(response.message.content)
        print(f'subtopics: {subtopics}')
        
        await ctx.set('subtopics', subtopics)
        await ctx.set('num_subtopics', len(subtopics))
        for subtopic in subtopics.values():
            ctx.send_event(SubtopicPackage(subtopic = subtopic))
    
    @step(num_workers=3)
    async def research_subtopics(self, ctx: Context, ev: SubtopicPackage) -> SubtopicSourceMaterialPackage:
        subtopic = ev.subtopic
        tavily_client = TavilyClient()
        response = tavily_client.search(subtopic)
        subtopic_materials = '\n'.join(result['content'] for result in response['results'])
        subtopic_urls = [result['url'] for result in response['results']]
        return SubtopicSourceMaterialPackage(subtopic_source_materials=subtopic_materials, urls=subtopic_urls)
    
    @step
    async def combine_research_subtopics(self, ctx: Context, ev: SubtopicSourceMaterialPackage) -> SourceMaterialPackage:
        num_packages = await ctx.get('num_subtopics')
        
        source_materials = ctx.collect_events(ev, [SubtopicSourceMaterialPackage] * num_packages)
        if source_materials is None:
            return None
        
        # Combine all source materials and URLs
        combined_materials = '\n'.join(result.subtopic_source_materials for result in source_materials)
        initial_urls = await ctx.get('initial_urls')
        all_urls = initial_urls + [url for result in source_materials for url in result.urls]
        return SourceMaterialPackage(source_materials=combined_materials, all_urls=all_urls)

    @step
    async def write_story(self, ctx: Context, ev: SourceMaterialPackage| EditorCommentaryPackage) -> DraftStoryPackage| StopEvent:
        if isinstance(ev, SourceMaterialPackage):
            print('writing story')
            topic = await ctx.get('topic')
            source_materials = ev.source_materials
            reference_urls = ev.all_urls
            llm = AzureOpenAI(
                engine="gpt-4o-mini",
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=10000
            )
            response = await llm.acomplete(f'''you are a world famous journalist. 
                                        you are tasked with writing a very detailed long form article about {topic}.
                                        these are some source materials for you to choose from and use to write the article: {source_materials}''')
            await ctx.set('draft_story', str(response))
            await ctx.set('reference_urls', reference_urls)
            return DraftStoryPackage(draft_story=str(response), reference_urls=reference_urls)
        
        else:
            print('writer refining draft story')
            topic = await ctx.get('topic')
            editor_commentary = ev.editor_commentary
            draft_story = await ctx.get('draft_story')
            reference_urls = await ctx.get('reference_urls')
            llm = AzureOpenAI(
                engine="gpt-4o-mini",
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=10000
            )
            response = await llm.acomplete(f'''you are a world famous journalist. 
                                        you are tasked with writing a very detailed long form article about {topic}.
                                        
                                        here is a draft of the report you wrote: {draft_story}
                                        here is the commentary from the editor: {editor_commentary}
                                        refine it to make it more engaging and interesting. your refined report, only put in name and content of the report.
                                        NO other commentary or metadata:''')
            return StopEvent(result={"story": str(response), "references": reference_urls})
    
    @step
    async def refine_draft_story(self, ctx: Context, ev: DraftStoryPackage) -> EditorCommentaryPackage:
        print('editor refining draft story')
        topic = await ctx.get('topic')
        draft_story = ev.draft_story
        
        llm = AzureOpenAI(
            engine="gpt-4o-mini",  
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=10000
        )
        response = await llm.acomplete(f'''you are a veteran newspaper editor. here is a draft of a long form article about {topic}: {draft_story}. 
                                           read it carefully and suggest ideas for improvement.''')
        return EditorCommentaryPackage(editor_commentary = str(response))

async def research_topic(topic: str):
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    w = ResearchWorkflow(timeout=10000, verbose=False)
    result = await w.run(query=topic)
    
    # Combine story and references into a single markdown string
    story = result["story"]
    reference_urls = result["references"]
    
    markdown_content = f"{story}\n\n## References\n"
    for i, url in enumerate(reference_urls, 1):
        markdown_content += f"{i}. {url}\n"
        
    return markdown_content

async def main():
    # Example topic to research
    topic = "artificial intelligence in quantum computing research"
    print(f"Researching topic: {topic}")
    markdown_content = await research_topic(topic)
    
    # Save the markdown content to a file
    filename = f"output/{topic.replace(' ', '_').lower()}_report.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print("\nFinal report:")
    print(markdown_content)
    print(f"\nReport saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(main()) 