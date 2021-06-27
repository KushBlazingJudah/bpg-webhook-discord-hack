import requests
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

BUCKET_LEFT = -1
BUCKET_RESET = 0

# inb4 you didn't compile!
REGEX_CITE = "<a.*class=\"quotelink\">&gt;&gt;(\d+)</a>"
REGEX_DEADLINK = "<span.*class=\"deadlink\">&gt;&gt;(\d+)</span>"
REGEX_QUOTE = "<span.*class=\"quote\">&gt;(.*)</span>"
REGEX_CODE = "<pre class=\"prettyprint\">([\s\S]*?)</pre>" # TODO: fix
REGEX_TITLE = "^/bpg/ - The Beginner Programmer&#039;s General"
REGEX_COMMENT = ".*https://rentry.co/bpg.*"

def set_ratelimit(req):
    global BUCKET_LEFT, BUCKET_RESET
    if req.status_code == 429 or req.json().get('message') == "You are being rate limited.":
        BUCKET_LEFT = 0
        BUCKET_RESET = time.time() + (float(req.json().get('retry_after')) / 1000)
        return

    try:
        BUCKET_LEFT = int(req.headers.get('X-RateLimit-Remaining'))
        BUCKET_RESET = float(req.headers.get('X-RateLimit-Reset'))
    except ValueError:
        print(f"discord returned invalid headers?\nremaining: {req.headers.get('X-RateLimit-Remaining')}\nreset at: {req.headers.get('X-RateLimit-Reset')}")
        print("leaving values as is")
    except IndexError:
        print("discord didn't return ratelimit headers")

def wait_ratelimit():
    print(BUCKET_LEFT, BUCKET_RESET, time.time())
    if BUCKET_LEFT == 0:
        time.sleep(BUCKET_RESET - time.time())

def fetch() -> list:
    global BOARD, THREAD_NUMBER, CACHE

    res = requests.get(f"https://a.4cdn.org/{BOARD}/thread/{THREAD_NUMBER}.json")
    if res.status_code != 200:
        print(res.content)
        return 0

    new = len(res.json()["posts"]) - len(CACHE)
    CACHE = res.json()["posts"]

    if res.json().get("archived", 0) == 1 or res.json().get("closed", 0) == 1:
        THREAD_NUMBER = 0

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

def push(post):
    wait_ratelimit()

    res = requests.post(WEBHOOK_URL, json={
        'content': fixup(post),
        'username': f"/bpg/ thread: No. {post['no']}"
    })

    set_ratelimit(res)

    if res.status_code != 200:
        print(f"error pushing {post['no']}\n", res.json())
        return False

    return True

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
                if not push(post):
                    print(f"retrying {post['no']}")
                    for i in range(3):
                        print(f"try {i}")
                        if not push(post):
                            if i == 3:
                                print("failed post")
                            continue
                        break

        time.sleep(CHECK_POSTS * 60)
    except Exception as e:
        print(e)
        print("waiting 30 seconds due to exception")
        time.sleep(30)
