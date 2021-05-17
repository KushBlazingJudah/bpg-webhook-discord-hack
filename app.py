import requests
import json
import time
import re
import html
import os

WEBHOOK_URL = os.environ['WEBHOOK_URL']
BOARD = "g"

CHECK_POSTS = 1
CHECK_THREAD = 5

THREAD_NUMBER = 0
LAST_FETCH = 0
CACHE = []

# inb4 you didn't compile!
REGEX_CITE = "<a.*class=\"quotelink\">&gt;&gt;(\d+)</a>"
REGEX_DEADLINK = "<span.*class=\"deadlink\">&gt;&gt;(\d+)</span>"
REGEX_QUOTE = "<span.*class=\"quote\">&gt;(.*)</span>"
REGEX_CODE = "<pre class=\"prettyprint\">([\s\S]*?)</pre>" # TODO: fix
REGEX_TITLE = "^/bpg/ - The Beginner Programmer&#039;s General"
REGEX_COMMENT = ".*https://rentry.co/bpg.*discord gg YfBUDU7GYn.*"

def fetch() -> list:
    global BOARD, THREAD_NUMBER, CACHE

    res = requests.get(f"https://a.4cdn.org/{BOARD}/thread/{THREAD_NUMBER}.json")
    if res.status_code != 200:
        print(res.content)
        return 0
    new = len(res.json()["posts"]) - len(CACHE)
    CACHE = res.json()["posts"]
    if res.json().get("archived", 0) == 1:
        THREAD_NUMBER = 1
    return new

def fixup(post):
    text = post['com'].replace("<br>", "\n")
    text = text.replace("<wbr>", "")
    text = re.sub(REGEX_CITE, lambda x: ">>" + x.group(1), text)
    text = re.sub(REGEX_DEADLINK, lambda x: f"~~>>{x.group(1)}~~", text)
    text = re.sub(REGEX_CODE, lambda x: f"`{x.group(1)}`" if x.group(1).find("\n") == -1 else f"```\n{x.group(1)}```", text)
    text = re.sub(REGEX_QUOTE, lambda x: ">" + x.group(1), text)
    text = text.replace("*", "\\*") # escape *THIS*
    text = text.replace("_", "\\_") # escape __this__
    text = html.unescape(text)

    tim = post.get('tim')
    if tim:
        text = f"https://i.4cdn.org/g/{tim}{post['ext']}\n{text}"

    if len(text) > 2000:
        truntext = f"\n**text truncated.** see https://boards.4channel.org/{BOARD}/thread/{THREAD_NUMBER}#p{post['id']} for full text"
        text = text[:len(text)-len(truntext)]
        text += truntext

    return text

def display(post):
    print(f"No. {post['no']}:\n{fixup(post)}")

def push(post):
    res = requests.post(WEBHOOK_URL, json={
        'content': fixup(post),
        'username': f"/bpg/ thread: No. {post['no']}"
    })

while True:
    try:
        if THREAD_NUMBER == 0:
            # look for thread
            res = requests.get(f'https://a.4cdn.org/{BOARD}/catalog.json')
            for page in res.json():
                for thread in page.get('threads', []):
                    if re.search(REGEX_TITLE, thread.get('sub', "")) and re.search(REGEX_COMMENT, thread.get('com', ""), re.MULTILINE):
                        THREAD_NUMBER = thread.get('no')
                        print(f"found thread {THREAD_NUMBER}")
                        break
                if THREAD_NUMBER != 0:
                    break
            if THREAD_NUMBER == 0:
                time.sleep(CHECK_THREAD * 60)
                continue

        new = fetch()
        print(f"{new} new posts")

        if new > 0:
            for post in CACHE[-new:]:
                print(f"pushing {post['no']}")
                push(post)

        time.sleep(CHECK_POSTS * 60)
    except Exception as e:
        print(e)
        time.sleep(30)
