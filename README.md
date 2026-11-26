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
| `members` | `[]` for anyone who can load the page, otherwise the names people pick from |
| `randomNames` | `true` (default): nobody types a name, and everyone appears under a random one that changes each visit. Ignored when `members` is set. |
| `keepHistory` | `false` wipes the room when the last person leaves, `true` keeps it |
| `historyMinutes` | Sliding window. Messages older than this disappear for everyone. Default `60`; `0` means no limit. |
| `assistant` | `true` downloads a small language model into each visitor's browser and answers messages that mention `@ai`. Default `false`. |
| `assistantModel` | The default WebLLM model, `Qwen2.5-0.5B-Instruct-q4f16_1-MLC`. Each visitor can pick another from a short list. |
| `assistantLib` | Where the WebLLM library is loaded from. Defaults to a pinned build on jsDelivr. |
| `sessionMinutes` | Auto-leave after this long. `0` means never. |
| `iceServers` | STUN/TURN list for direct mode. `[]` means same network only. |
| `bucketRoot` | `""` to auto-detect, or `"/"` or `"/my-bucket/"` to force |

## The assistant

When `assistant` is on, each visitor's browser downloads a small language model in the background while they read the entry screen (a few hundred MB, once; the browser caches it). It runs entirely on the visitor's device using WebGPU through [WebLLM](https://github.com/mlc-ai/web-llm), in a background worker so the page stays responsive while it thinks. Nothing is sent to an AI service.

- Write `@ai` in a message to ask it something. The reply is produced on the asker's own device and posted to the room, labelled with who asked.
- It gets the question plus the last few messages as optional background.
- Each visitor can pick the model from a short list, on the entry screen or by tapping the assistant label in the room. The choice is remembered on their device, and a newly chosen model is downloaded once.
- The models are small. Expect short, simple answers, and do not rely on them for facts, code or reasoning. In a side-by-side try, Qwen2.5 0.5B (the default) coped best with chat context, LFM2.5 350M was close, and SmolLM2 360M was the weakest but smallest.
- Browsers without WebGPU, or with data saver on, skip the download and the chat works as normal.
- On graphics hardware without 16-bit float support, the page switches to the 32-bit build of the same model automatically.

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
