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
- [ ] Passkeys?

### Blog

- [X] MicroPub server
- [X] WebSub
- [ ] Feed: h-feed, RSS/ATOM (with XSL), JSON
  - [X] card
  - [X] note
  - [X] article
  - [X] like
  - [X] bookmark
  - [ ] checkin
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
- [ ] Logging
- [ ] CRUD
- [ ] Bookmarklets
- [ ] Local replies/likes
- [ ] PWA
- [ ] Syndication (FAWM, Archive.org, Bandcamp, IndieWeb News)
- [ ] MicroPub client
- [ ] ActivityPub
- [ ] Payments

### Quantified self

- [ ] Oura (steps, sleep hours, hearbeat)
- [ ] Withings
- [ ] Listens
- [ ] Air quality

### Reader

- [ ] MicroSub
- [ ] WebSub
  - Subscribe to things by posting a https://indieweb.org/follow
    - Add to trusted domains
- [ ] ActivityPub

### Music

- [ ] <link rel="music-collection" />
    - Or maybe just post to micropub endpoint?
- [ ] bookmarklet to get song from Bandcamp, FAWM, etc.

### Other

- [ ] Gemini
- [ ] Titan?

### Notes

- call /publish on new entries => event
- fix rel="self" so it works in categories, main page, etc

https://indieweb.org/h-x-app#Properties
- extract more info when app requests a token

- render responses (https://indieweb.org/responses), and return in feed
    - do more work to populate a summary, specially for websites without an h-entry

- private/unlisted/public and draft/published
    - create untrusted webmentions as private/draft
    - remove content coumn from incoming_webmentions and outgoing_webmentions

- store logins in a table
- UI for seeing applications and revoking access

- webmention moderation (simply make it a draft)
- replies to places that don't receive webmentions?

- on auth.html, ask for confirmation on giving refresh token and the expiration time of the access token

/bookmarklet blueprint
- Gives Bookmarklets pre-filled if logged in
- Used for like/bookmark/repost/reply/song

- ask for scope when using indieauth
  - put indieauth as the first provider


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
