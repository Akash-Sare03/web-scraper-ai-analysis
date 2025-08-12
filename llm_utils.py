# llm_utils.py
from groq import Groq
import markdown2
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def ask_groq_llm(extracted_text, user_query):
    """
    Send extracted HTML content and user query to Groq LLM,
    keeping prompt within safe token limits.
    """

    # ✅ Truncate the extracted text more aggressively (~3000 tokens = 10k chars)
    max_chars = 10000
    truncated_text = extracted_text[:max_chars] if extracted_text else ""

    # ✅ Simple safety check
    if not truncated_text.strip():
        return "No usable content to send to LLM."

    # ✅ Full prompt (very compact and clean)
    full_prompt = f"""
From the following HTML text:

\"\"\"{truncated_text}\"\"\"

Answer this user question briefly and in tabular format if possible:

\"{user_query}\"
"""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "You're a data assistant that extracts meaningful information from HTML text and answers in a clean table."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.5,
        )

        markdown_content = response.choices[0].message.content
        html_content = markdown2.markdown(markdown_content, extras=["tables"])  # convert markdown to HTML
        return html_content

    except Exception as e:
        return f"Error from Groq: {str(e)}"
