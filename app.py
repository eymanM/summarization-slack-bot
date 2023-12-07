import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from unstructured.cleaners.core import remove_punctuation, clean, clean_extra_whitespace
from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import SeleniumURLLoader
from dotenv import load_dotenv

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))


def generate_document(url):
    loader = SeleniumURLLoader(urls=[url], )
    elements = loader.load()
    text = clean_extra_whitespace(remove_punctuation(clean(elements[0].page_content)))
    return Document(page_content=text, metadata={"source": url})


def summarize_document(url):
    openai_chat = ChatOpenAI(model_name="gpt-3.5-turbo-1106")
    chain = load_summarize_chain(openai_chat, chain_type="stuff")
    tmp_doc = generate_document(url)
    summary = chain.run([tmp_doc])
    return clean_extra_whitespace(summary)


@app.event("app_mention")
def handle_app_mention_events(event, say, logger):
    urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', event["text"])

    if len(urls) == 0:
        say(text='No URL found')
        return

    output = summarize_document(urls[0])
    say(text=f"Here is is:\n{output}")

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

