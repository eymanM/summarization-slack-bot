import os
import re
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from langchain.chat_models import ChatOpenAI
from langchain.docstore.document import Document
from unstructured.cleaners.core import remove_punctuation, clean, clean_extra_whitespace
from langchain.chains.summarize import load_summarize_chain
from langchain.document_loaders import SeleniumURLLoader
from flask import Flask, request
import logging

logging.basicConfig(level=logging.DEBUG)
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)


def generate_document(url):
    loader = SeleniumURLLoader(urls=[url], headless=True, browser='chrome',
                               executable_path=os.environ.get("CHROMEDRIVER_PATH"),
                               binary_location=os.environ.get("GOOGLE_CHROME_BIN"),
                               arguments=['--no-sandbox', '--disable-dev-shm-usage', '--headless', '--disable-gpu'])
    elements = loader.load()
    logging.debug(f'elements: {elements}')
    text = clean_extra_whitespace(remove_punctuation(clean(elements[0].page_content)))
    return Document(page_content=text, metadata={"source": url})


def summarize_document(url):
    openai_chat = ChatOpenAI(model_name="gpt-3.5-turbo-1106")
    chain = load_summarize_chain(openai_chat, chain_type="stuff")
    logging.debug(f'Summarizing {url}')
    tmp_doc = generate_document(url)
    summary = chain.run([tmp_doc])
    return clean_extra_whitespace(summary)


@app.event("app_mention")
def handle_app_mention_events(event, say, logger):
    print('enter to app_mentions')
    logger.info(f"event text: {event['text']}")
    urls = re.findall(r'(https?://\S+)', event['text'].strip().replace('>', ''))
    if len(urls) == 0:
        say(text='No URL found')
        return

    logger.info(f"URLs found: {urls}")
    output = summarize_document(urls[0])
    say(text=f"Here it is:\n{output}")


flask_app = Flask(__name__)
handler = SlackRequestHandler(app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    logging.debug('slack_events')
    return handler.handle(request)


@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>')
def catch_all(path):
    logging.debug('catch all')
    print('catch all')
    return 'No content'


if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
