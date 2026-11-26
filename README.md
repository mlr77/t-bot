# t-bot

A working folder for browser-only experiments: pages that need no server of their own. The main one is **Ephemeral Room**, a chatroom in a single static HTML file that runs from any static host: GitHub Pages, or an access-controlled, S3-style bucket.

- No accounts and no typed names: everyone gets a random name each visit.
- Messages disappear after an hour. Anyone can keep their own copy with **Save chat**.
- An optional small AI assistant runs inside each visitor's browser and answers messages that mention `@ai`.

## Files

- `ephemeral-room.html`: the chat page. Text, pasted code, attachments, a file explorer, a text compare tool and the assistant.
- `ephemeral-room.config.json`: optional owner settings, read from the same folder as the page.
- `bucket-check.html`: a small page that tests whether the bucket supports what the chat needs. Run this first.
- `mock-bucket.py`: a local stand-in for the bucket, for trying the chat on one machine.
- `index.html`: a front door that forwards to the chat page, so the site's root link works.
- `tiny-chat.html`: a standalone experiment. One person chatting with a small model that runs in their own browser, with model choice, streaming and speed readouts.

## Setup

1. Upload `bucket-check.html` to the bucket and open it while signed in. All five steps should pass.
2. Upload `ephemeral-room.html` and, optionally, `ephemeral-room.config.json` to the same folder.
3. Give write access on the config file to the chat owner only.
4. Share the page link. Everyone who opens it lands in the same room.

Signed-in users need to list, read, write and delete under `_ephemeral-room/` in the page's folder, using plain same-origin requests.

## Run it from GitHub Pages

GitHub Pages is read-only, so shared storage cannot work there. Instead the page uses its relay transport: public relay servers introduce browsers to each other, and messages then travel directly between them. Nothing is stored.

1. In the repo, open Settings, then Pages. Under "Build and deployment", choose "Deploy from a branch", branch `main`, folder `/ (root)`, and save.
2. After a minute or so the site is live at `https://<user>.github.io/<repo>/`.
3. Share that link. Everyone who opens it lands in the same room. Add `#some-name` for a separate room.

This works because `ephemeral-room.config.json` in this repo sets `"fallback": "relay"`. The relay transport loads the [Trystero](https://github.com/dmotz/trystero) library from a CDN at a pinned version.

## Try it locally

No bucket yet? Run the stand-in server from this folder (Python 3, nothing to install):

```sh
python3 mock-bucket.py
```

Then open `http://localhost:8000/ephemeral-room.html` in two browser tabs. Each tab should show the other within a couple of seconds. `http://localhost:8000/bucket-check.html` should pass all five steps.

Add `--read-only` to see what happens when storage can't be used. Messages are held in memory and vanish when the server stops. GitHub Pages cannot play this role, because it is read-only.

## Settings

| Key | Meaning |
| --- | --- |
| `transport` | `"storage"` (default), `"relay"` or `"direct"` |
| `fallback` | Used when storage can't be reached: `"direct"` (default, invite codes) or `"relay"` |
| `relayLib` | Where the relay library is loaded from. Defaults to a pinned Trystero build on jsDelivr. |
| `relayAppId` | Namespace on the public relays. Change it to keep your rooms apart from other copies of this page. |
| `defaultRoom` | Room used when the link has no `#name`. `""` makes a new private room. |
| `autoEnter` | `true` (default): a link with a passcode after the `#` skips the start page. Needs random names. |
| `members` | `[]` for anyone who can load the page, otherwise the names people pick from |
| `randomNames` | `true` (default): nobody types a name, and everyone appears under a random one that changes each visit. Ignored when `members` is set. |
| `keepHistory` | `false` wipes the room when the last person leaves, `true` keeps it |
| `historyMinutes` | Sliding window. Messages older than this disappear for everyone. Default `60`; `0` means no limit. |
| `assistant` | `true` downloads a small language model into each visitor's browser and answers messages that mention `@ai`. Default `false`. |
| `assistantModel` | The default WebLLM model, `Qwen2.5-0.5B-Instruct-q4f16_1-MLC`. Each visitor can pick another from a short list. |
| `house` | `true` turns on the house characters. Default `false`. |
| `feed` | Where new items come from; see the table under watch-only rooms. New items become conversation starters. |
| `language` | Language for the characters and feed summaries, for example `"Simplified Chinese"`. |
| `watch` | `true` makes a watch-only room: no message box, one character remark per feed item. |
| `rooms` | Named specialty rooms: `{ "name": { "title", "house", "feed", "language", "watch", "feedMinutes", "assistantModel" } }`. A room's model overrides the visitor's remembered choice while they are in it. |
| `assistantLib` | Where the WebLLM library is loaded from. Defaults to a pinned build on jsDelivr. |
| `sessionMinutes` | Auto-leave after this long. `0` means never. |
| `iceServers` | STUN/TURN list for direct mode. `[]` means same network only. |
| `bucketRoot` | `""` to auto-detect, or `"/"` or `"/my-bucket/"` to force |

## Private rooms and passcodes

The plain link opens the shared room, with a start page. Anything after a `#` in the link is a room passcode: it names a separate, private room and is also the key that encrypts it.

- Type a passcode on the start page, or press **Create private room** for a long random one.
- Inside the room, **Copy link** gives a link that includes the passcode. Anyone who opens it lands straight in the chat, with no start page.
- **Leave** returns to the start page of the shared room.
- The passcode is never shown on screen; the header shows a short fingerprint instead.
- A short or guessable passcode is a guessable room. Use a long one, or the generated link.

Set `autoEnter` to `false` to always show the start page.

## The assistant

When `assistant` is on, each visitor's browser downloads a small language model in the background while they read the entry screen (a few hundred MB, once; the browser caches it). It runs entirely on the visitor's device using WebGPU through [WebLLM](https://github.com/mlc-ai/web-llm), in a background worker so the page stays responsive while it thinks. Nothing is sent to an AI service.

- Write `@ai` in a message to ask it something. The reply is produced on the asker's own device and posted to the room, labelled with who asked.
- **What it can see** is a choice next to the model picker. "The whole chat" hands it as much of the current window as fits its memory (about 4,000 tokens). "Only related messages" hands it the messages that share words with the question, their neighbours, and the last few, and switches to the whole chat when asked for a summary. "Automatic" picks the whole chat for the 1B models and related messages for the smaller ones.
- It is not shown its own earlier replies, so a follow-up should restate what it refers to.
- Each visitor can pick the model from a short list, on the entry screen or by tapping the assistant label in the room. The choice is remembered on their device, and a newly chosen model is downloaded once.
- The models are small. Expect short, simple answers, and do not rely on them for facts, code or reasoning. In a try with a 45-message planning chat, Gemma 3 1B used the history most reliably, Llama 3.2 1B was next, and the models at 0.5B and below often missed or mixed up details, including a plan that changed partway through.
- Browsers without WebGPU, or with data saver on, skip the download and the chat works as normal.
- On graphics hardware without 16-bit float support, the page switches to the 32-bit build of the same model automatically.

## House characters and feeds

With `house` on, three AI regulars (Mochi, Rook and Pixel) keep the room from sitting empty. They are played by the same in-browser model as the assistant.

- **Quiet room:** one of them starts a topic. They trade a few lines, then go quiet until a person replies or enough time passes.
- **Conversation going:** one of them chimes in after a person's message. Messages addressed to `@ai` are left to the assistant.
- **No host needed:** every open browser with a ready model can speak for them. Each waits a random time, and any house message it sees resets its wait, so normally only one speaks. The room stays lively for as long as at least one such browser is open.
- **Feed:** set `feed` to `hackernews`, or to the address of an RSS or Atom feed, and new items are posted by "Newswire" with a one-line summary for the characters to discuss. Browsers can only read feeds whose sites allow it; Hacker News does, many plain RSS feeds do not.
- **Language:** set `language` and the characters and summaries use it. Name the language in itself as well, for example `简体中文 (Simplified Chinese)`; the models follow that far better. In a try with real models, Qwen2.5 1.5B wrote natural Chinese, Qwen2.5 0.5B wrote Chinese with mistranslations, and Gemma 3 1B ignored the instruction and answered in English.
- **Specialty rooms:** entries under `rooms` in the settings file are named rooms with their own title, feed and language. They appear as buttons on the start page. Their names are public, so they are open rooms, not private ones.
- Each person can hide the house characters on their own device from the assistant panel.

## Watch-only rooms

A specialty room with `watch` set to `true` has no message box. "Newswire" posts each new feed item, and one house character makes a single remark about it. The repo's example is `#live-wire`, which follows new Hacker News submissions.

Feed sources a browser is allowed to read, all tried from a real browser:

| `feed` value | What it follows |
| --- | --- |
| `hackernews` | Hacker News top stories |
| `hackernews-new` | Every new Hacker News submission |
| `bluesky:<handle>` | One Bluesky account's posts, for example `bluesky:bsky.app` |
| `bluesky-feed:<at:// address>` | A Bluesky feed such as "What's Hot" |
| `mastodon:<server>#<tag>` | A hashtag on a Mastodon server, for example `mastodon:mastodon.social#astronomy` |
| an `https://` address | An RSS or Atom feed, if its site allows browsers to read it |

X and Weibo cannot be read from a static page: both need a signed-in API and neither allows browser requests from other sites. Following them would take a small scheduled job that fetches the posts and writes them to a file this page can poll.

Public timelines are unfiltered. A firehose such as "What's Hot" can put anything on the page, and the characters will comment on it, so following chosen accounts or tags is safer.

## Deleting, editing and clearing

- **Delete** and **Edit** appear on your own messages. The change reaches every open browser, and people who join later never see the old version.
- Only the author can do this: each message carries the hash of a secret that only the author's browser holds, and a delete or edit has to present the secret.
- **Clear view** empties the chat on your device only.
- **Clear for everyone** exists only in passcode rooms, where everyone present was given the link.
- These are requests to well-behaved browsers, not a recall. Anything already saved, copied or screenshotted stays where it is.

## History and saving

Messages older than `historyMinutes` (one hour by default) are removed from every open tab, are not passed on to people who join later, and in storage mode are deleted from the bucket. **Save chat** downloads the messages currently on screen as a text file on that person's own device. Attachments are listed by name but not included; save those individually.

## How it works

- **Storage transport:** each message is an encrypted object in a per-room folder, and open tabs poll that folder.
- **Relay transport:** for hosts with no writable storage. Public Nostr relays (via Trystero) introduce browsers to each other, then messages go directly between browsers. Relays see encrypted handshakes, IP addresses and timing, not content.
- **Direct transport:** WebRTC data channels in a full mesh, started by a manual two-code swap. The last resort when neither of the others can be used.
- Everything is encrypted with a key derived from the room name in the link's `#fragment`.

## Limits

- Anyone can label a message as coming from the assistant; the label is a convenience, not a guarantee.
- Random names hide who is who from other people in the room. They do not hide it from the network: in relay and direct modes browsers connect to each other and can see IP addresses, and in storage mode the bucket's own access logs may record who wrote what.
- The member list is a pick-list, not a lock. The page cannot tell who is signed in; real access control is the bucket's own access list.
- Anyone who can load the page and knows a room's name can derive that room's key.
- The last-person wipe is best effort. Add an expiry rule on `_ephemeral-room/` as a backstop.
- Relay and direct modes are peer-to-peer, so networks that block those connections need a TURN server in `iceServers`, and a room only exists while someone has it open.
- Storage mode is tested against the mock server in this repo, not yet against a real bucket.

## License

[MIT](LICENSE). The relay transport loads [Trystero](https://github.com/dmotz/trystero) and the assistant loads [WebLLM](https://github.com/mlc-ai/web-llm) from a CDN at run time; they and the models they download are covered by their own licenses.
