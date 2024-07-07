# robida.net

My website.

## TODO

### Infra

- [X] IndieAuth
- [X] RelMeAuth
- [X] Centralized login
- [X] IndieAuth provider
- [X] Robots.txt
- [X] Backup
- [ ] Firefox storage
- [ ] OpenStreetMap provider
write_diary
https://wiki.openstreetmap.org/wiki/OAuth#OAuth_2.0
- [ ] Passkeys

### Blog

- [X] MicroPub server
- [X] WebSub
- [ ] Feed: h-feed, RSS/ATOM (with XSL), JSON
  - [X] h-card
  - [X] note
  - [X] article
  - [X] like
  - [X] bookmark
  - [X] checkin
  - [ ] reply
  - [ ] repost
  - [ ] event
  - [ ] issue
  - [ ] rsvp
  - [ ] geocache
  - [ ] read
  - [ ] trip
  - [ ] venue (h-card)
  - [ ] song
  - [ ] listens (use song.link)
  - [ ] photo/image
- [X] Search
- [X] Single entry display
- [ ] WebMentions
  - [X] Salmentions
  - [ ] Manual webmentions
  - [ ] Private webmentions
- [X] SCSS
- [X] Categories
- [X] Pages
  - [X] About
  - [X] Contact
  - [X] Now
- [X] Event dispatcher
- [ ] MicroPub extensions
  - [X] Post status
  - [X] Visibility
  - [ ] Supported vocabulary
  - [ ] Post list
  - [ ] Category list
  - [ ] Contacts
- [X] CRUD
  - [X] Create
  - [X] Delete
  - [X] Edit
- [ ] Logging
- [ ] Bookmarklets
  - [ ] Like
  - [ ] Bookmark
  - [ ] Reply
  - [ ] Repost
  - [ ] Song (FAWM, Bandcamp, YouTube, etc.)
- [ ] Local replies/likes
- [ ] PWA
- [ ] Syndication
  - [ ] FAWM
  - [ ] Archive.org
  - [ ] Bandcamp
  - [ ] IndieWeb News
  - [ ] OSM diary
- [ ] MicroPub client
- [ ] ActivityPub
- [ ] Payments

### Quantified self

- [ ] Oura (steps, sleep hours, hearbeat)
- [ ] Withings
- [ ] Air quality
- [ ] Song listens

### Reader

- [ ] MicroSub
- [ ] WebSub
  - [ ] Subscribe by posting a https://indieweb.org/follow?
  - [ ] Add followers to trusted domains
- [ ] ActivityPub

### Other

- [ ] Gemini
- [ ] Titan?

### Notes

- checkbox on edit post to update timestamp
  - feed should order by updated (it does)
- confirm before closing edit/new if there are unsaved changes

- Have canonical form for each type, and conform to it on micropub endpoint
    Actually, store content as is, but conform when reading!
- Render all entry types as cards, like the check-in

- have a "shipment" type for tracking packages
  - it should send notification when the status changes

- call /publish on new entries => event
- fix rel="self" so it works in categories, main page, etc

https://indieweb.org/h-x-app#Properties
- extract more info when app requests a token

- render responses (https://indieweb.org/responses), and return in feed
    - do more work to populate a summary, specially for websites without an h-entry

- store logins in a table
- UI for seeing applications and revoking/extending access

- replies to places that don't receive webmentions?

- on auth.html, ask for confirmation on giving refresh token and the expiration time of the access token
    - need this for indiepass, which doesn't refresh the token!

- ask for scope when using indieauth to login

- move db.execute out of API?
- index should point to tags on veganism/indieweb, etc?
- https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/
- https://chatgpt.com/c/aa0c1dc8-03e7-40e7-91dd-7cc6708f23d6
- if category is URL, convert to hcard for people tagging
- likes and replies by logging in with URL in my website
    - if the website supports micropub we could even post to it (repost/reply/like)

- Media
https://developers.google.com/actions/media
https://github.com/sigma67/ytmusicapi

h-resume

Tracking shipments
https://docs.easypost.com/guides/tracking-guide  ($0.02 per tracker)
https://chatgpt.com/c/fd8e7f97-fdb5-4064-afc1-0442c8325cbd
https://chatgpt.com/c/c96c11c2-61b8-48ec-b265-e589d5455500
https://opencagedata.com/pricing#geocoding-onetime : ZIP to lat/lon

<p>My name is <ruby class="p-name">Beto Dealmeida<rp>(</rp><rt>/ <span class="p-ipa">bɛtto de aʊˈmeɪ da</span> /</rt><rp>)</rp></ruby>.</p>

https://github.com/ariebovenberg/whenever


# OSM syndication
curl 'https://www.openstreetmap.org/diary' -X POST -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:128.0) Gecko/20100101 Firefox/128.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://www.openstreetmap.org/diary/new' -H 'Content-Type: application/x-www-form-urlencoded' -H 'Origin: https://www.openstreetmap.org' -H 'DNT: 1' -H 'Sec-GPC: 1' -H 'Connection: keep-alive' -H 'Cookie: _osm_location=-80.16406|25.68716|19|M; _osm_session=106b8072574613389ed1a202cb562f31; _osm_banner_sotmeu_2024=1; _osm_totp_token=511039; _osm_banner_sotm_2024=2' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'TE: trailers' --data-raw 'authenticity_token=S06WitFWKgGGwyvqEABPf0TfuiQo9IsNnpOErvv7ayqUwYggKWtvIfnzs77Z7GmNcqoBk9QbNfuc01gysKbIOw&diary_entry%5Btitle%5D=Hello%2C+world%21&diary_entry%5Bbody%5D=I+started+contributing+some+edits+to+OSM+using+%5BStreetComplete%5D%28https%3A%2F%2Fstreetcomplete.app%2F%29%2C+it%27s+nice+to+be+able+to+help%21&diary_entry%5Blanguage_code%5D=en&diary_entry%5Blatitude%5D=25.69375605192825&diary_entry%5Blongitude%5D=-80.1629662513733&commit=Publish'


PRAGMA foreign_keys = ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA mmap_size = 134217728;
PRAGMA journal_size_limit = 27103364;
PRAGMA cache_size=2000;
https://blog.pecar.me/sqlite-prod

Use YARL

https://kiko.io/post/My-well-known-feeds-and-thoughts-beyond/
https://kiko.io/post/Head-Care/

Automate https://github.com/ai-robots-txt/ai.robots.txt

http://microformats.org/wiki/representative-h-card-parsing

- p-sound with my own voice
- nickname, given name, family name
- photo

