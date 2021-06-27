# bpg-webhook-discord-hack
This is a little script that checks 4chan's API to mirror threads to #thread on
the /bpg/ Discord using a webhook.

It isn't written well, but it is what it is.

## Running
Ensure you have Requests installed.

Modify the script (`app.py`) to fit your needs, and run it providing a Discord
webhook URL in the environment variable `WEBHOOK_URL`.

It should be in a form like this:
`https://discord.com/api/webhooks/<numbers>/<long_string>?wait=true`

It is **VERY** important to add the `?wait=true` at the end or **YOU WILL
EVENTUALLY RUN INTO RATE LIMITING PROBLEMS.**
This also allows us to confirm that the message was sent successfully and didn't
fail.
