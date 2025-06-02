import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from googleapiclient.discovery import build
from openai import OpenAI

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client_ai = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def search_islamqa_multiple(query, max_results=5):
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = service.cse().list(
            q=f"{query} site:islamqa.info",
            cx=GOOGLE_CSE_ID,
            num=max_results
        ).execute()
        results = []
        if 'items' in res:
            for item in res['items']:
                title = item.get('title')
                link = item.get('link')
                snippet = item.get('snippet', '')
                results.append({'title': title, 'link': link, 'snippet': snippet})
        return results
    except Exception as e:
        print(f"Google API error: {e}")
        return []

def summarize_with_llm(results, question):
    sources_text = "\n\n".join([
        f"Title: {res['title']}\nSnippet: {res['snippet']}" for res in results
    ])
    prompt = f"""
You are a knowledgeable Islamic scholar writing in the style of Tafsir Ibn Kathir.

**Question:** {question}

Below are scholarly summaries from IslamQA regarding this issue (not all the information may be relevant to the question however,
could even be just a little).:

{sources_text}

Based only on the content provided above:
- Write a comprehensive, scholarly, evidence-based answer.
- Your answer must follow the style of Tafsir Ibn Kathir: authoritative, structured, and grounded in authentic sources.
- Include direct Quranic verses and Hadiths (only if mentioned in the snippets), and reference them clearly.
- Do not summarize Hadith or Quran unless the snippet does. Quote them directly when possible.
- Do not fabricate any rulings or details. Use only what is presented in the snippets.
- Avoid referencing usernames, messages, or summary formatting.
"""
    try:
        response = client_ai.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI summarization error: {e}")
        return "❌ Error generating summary. Please try again later."

@bot.command(name='ask')
async def ask(ctx, *, question):
    try:
        await ctx.send(f"🔍 Searching IslamQA for: **{question}**")
        results = search_islamqa_multiple(question, max_results=5)

        if not results:
            await ctx.send("❌ No results found from IslamQA.")
            return

        summary = summarize_with_llm(results, question)

        embed = discord.Embed(
            title=f"📘 Answer to: {question}",
            description=summary,
            color=discord.Color.green()
        )

        for i, res in enumerate(results[:5], start=1):
            embed.add_field(name=f"🔗 Source {i}", value=f"[{res['title']}]({res['link']})", inline=False)

        embed.set_footer(text="Summarized from IslamQA.info")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ An error occurred: `{str(e)}`")
        print("Unhandled error in ask command:", e)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

bot.run(DISCORD_BOT_TOKEN)
