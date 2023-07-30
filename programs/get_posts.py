import time
import asyncio
import aiohttp
import requests
import pypandoc


async def fetch(session, post_id):
    url = "https://hacker-news.firebaseio.com/v0/item/{post_id}.json".format(post_id = post_id)

    try:
        async with session.get(url) as response:
            return await response.json()
    except:
        return


async def call_apis(post_ids):
    async with aiohttp.ClientSession(trust_env=True) as session:
        tasks = []
        for post_id in post_ids:
            tasks.append(asyncio.ensure_future(fetch(session, post_id)))
        responses = await asyncio.gather(*tasks)
        return responses


def filter_post(post):
    is_a_valid_story = \
            post \
            and post.get('type') == "story" \
            and post.get("title") \
            and post.get("url")

    return is_a_valid_story


def read_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    return content


if __name__ == "__main__":
    fetch_block_size = 10**4 # how many posts to fetch at once
    duration = 31557600
    
    current_unix_timestamp = time.time()
    posts_minimum_timestamp = current_unix_timestamp

    max_id = requests.get("https://hacker-news.firebaseio.com/v0/maxitem.json").json()
    last_seen_id = max_id

    posts = []

    while (posts_minimum_timestamp >= current_unix_timestamp - duration):
        percentage_done = round(
          100 * (current_unix_timestamp - posts_minimum_timestamp) / duration,
          ndigits = 2
        )

        print(str(percentage_done) + "%")

        post_ids = range(last_seen_id - fetch_block_size, last_seen_id + 1)

        post_block = asyncio.run(call_apis(post_ids))

        try:
            posts_minimum_timestamp = min([post.get("time") for post in post_block])
        except:
            print("post block error")

        post_block = [post for post in post_block if filter_post(post)]
        posts.extend(post_block)
        last_seen_id = last_seen_id - fetch_block_size

    sorted_posts = sorted(
        posts,
        key  = lambda post: post.get("score"),
        reverse = True
        ) \
        [0:50]

    posts = "\n".join(["1. [{title}](https://news.ycombinator.com/item?id={id})".format(title = post.get("title"), id = post.get("id")) for post in sorted_posts])

    # work around pypandoc errors with -H option
    text = \
        read_file("programs/header.html") \
        + pypandoc.convert_text(posts, 'html5', format = 'md') \
        + read_file("programs/footer.html")

    with open("output/index.html", "w") as f:
        f.write(text)
