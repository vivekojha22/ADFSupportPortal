import streamlit as st
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import re
import requests
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = "gpt-4o-mini"  # Use your actual deployment name
AZURE_OPENAI_API_VERSION = "2024-02-15-preview"

client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

# --- Helper Functions ---

def sanitize_input(text):
    # Basic PII-like pattern removal
    text = re.sub(r'\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b', '[REDACTED-SSN]', text)
    text = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w{2,4}\b', '[REDACTED-EMAIL]', text)
    text = re.sub(r'\b(?:\+?\d{1,3})?[-.\s]?(?:\(?\d{3}\)?)[-.\s]?\d{3}[-.\s]?\d{4}\b', '[REDACTED-PHONE]', text)
    return text

def search_public_forums(query, num_results=3):
    search_results = []
    headers = {"User-Agent": "Mozilla/5.0"}
    query = query + " site:learn.microsoft.com OR site:stackoverflow.com OR site:reddit.com"
    search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"

    res = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    for g in soup.find_all('div', class_='tF2Cxc')[:num_results]:
        link = g.find('a', href=True)
        if link:
            search_results.append(link['href'])
    return search_results

def get_ai_response(issue_description, links):
    prompt = f"""
You are a support agent specialized in Azure Data Factory and Fabric Data factory. A user has reported the following issue:

'{issue_description}'

You searched the internet and found these resources:
{chr(10).join(links)}

Please generate a clean, easy-to-understand explanation of the issue and suggest a resolution. If possible, refer to any useful links.
"""

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You are a helpful support assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()

# --- Streamlit UI ---

st.set_page_config(page_title="ADF Support AI", layout="centered")
st.title("🛠️ Azure Data Factory Support Portal")

with st.form("issue_form"):
    issue_description = st.text_area("Describe the issue (no PII):", height=200)
    submitted = st.form_submit_button("Get Solution")

if submitted and issue_description:
    with st.spinner("Analyzing and searching for the best solution..."):
        clean_input = sanitize_input(issue_description)
        links = search_public_forums(clean_input)
        ai_solution = get_ai_response(clean_input, links)

    st.subheader("✅ Suggested Solution")
    st.markdown(ai_solution)

    st.subheader("🔗 References")
    for link in links:
        st.markdown(f"- [{link}]({link})")
