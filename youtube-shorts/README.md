# MarketOpsTips YouTube Shorts

A daily agent makes 3 voiced Shorts for the MarketOpsTips channel (marketing tip 6:30 AM, business fact 1:30 PM, interesting fact 7:30 PM IST) and sends them to the owner, who schedules them in YouTube Studio.

- `engine/make_short.py` turns a storyboard JSON into a 1080x1920 MP4 with an English voiceover (Kokoro, Apache 2.0), captions, brand visuals and music made in code.
- `topics.json` holds the 30-day plan with key facts. After day 30 the agent picks new topics.
- `state/progress.json` tracks the next day and topics already used.
- `out/<date>/` keeps each day's storyboards and `upload.md` (titles, descriptions, times). Videos are not stored in git.

Storyboard: `{id, pillar, title, description, beats: [{say, show, emoji?, big?}]}`. In `show`, wrap words in [brackets] to colour them lime. `big` is a short number or word shown large.
