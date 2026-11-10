# MarketOps brand video style

Reference: videos/MarketOps-Brand-Intro-69s-1440p.mp4 (1440p remake of videos/MarketOps-Brand-Intro-69s.mp4) (approved by the owner on 10 Nov 2026).
Every new video for the MarketOps YouTube channel should follow this style.

Style
- Always 2560x1440 (1440p), 30 fps, as the owner asked on 10 Nov 2026. The first intro was made at 1920x1080; build new videos natively at 1440p (scale all sizes by 4/3), never by upscaling a 1080p render. Thumbnails stay 1280x720 (YouTube's size). Dark page background #131313 with a soft centre lift, lime #C6F24E only on 1-2 words per screen, Inter ExtraBold/Bold, sentence case.
- Kinetic text: words rise into place one after another; short lines ("Look better. Speak louder. Grow smarter.").
- Scenes: logo reveal with lime underline, card fan of MarketOps post images (daily/*), tilted wall of posts, website mockup (marketops.in browser frame), numbered service list (big faint numbers, dash progress), value cards (olive badge + lime line icon + faint 01-04), outro with logo, hello@marketops.in and lime marketops.in button, fade to black.
- Thin lime progress bar along the bottom.
- Voice: Kokoro af_heart (Apache 2.0), speed about 1.12. Music made in code (118 bpm, kick, clap, hats, bass, pad), ducked under the voice, whoosh on scene changes, loudness -14 LUFS.
- Deliver MP4 + English .srt + 2 thumbnails (1280x720) + title, short description and tags.

Files
- lines.json: voiceover lines. vo.py makes vo_XX.wav (python3 vo.py af_heart 1.12; model files in kokoro dir).
- promo.py draws in 1920x1080 design units and renders natively at 2560x1440 (K = 4/3, SD() draws scaled, new() makes scaled layers, logo_w() scales the logo). GROUPS maps lines to scenes; SCENES lists the scene functions. `python3 promo.py audio`, then `frames t1,t2` to preview, then `render a b out.mp4` in parallel chunks, concat, add mix.wav.
- thumb.py: thumbnails.
Paths inside the scripts point to the scratch folder they were written in; adjust HERE/S before reuse.
