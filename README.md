# robida.net

My website.

## TODO

### Infra

- [X] IndieAuth
- [X] RelMeAuth
- [ ] Centralized login
- [ ] OpenStreetMap provider
- [ ] Passkeys?

### Blog

- [X] MicroPub
- [X] WebSub
- [/] Feed: h-feed, RSS/ATOM (with XSL), JSON
  - [X] note
  - [X] card
  - [X] article
  - [ ] reply
  - [ ] repost
  - [ ] like
  - [ ] bookmark
  - [ ] event
  - [ ] issue
  - [ ] rsvp
  - [ ] geocache
  - [ ] read
  - [ ] checkin
  - [ ] trip
  - [ ] venue (h-card)
  ------
  - [ ] song
- [X] Search
- [X] Single entry display
- [/] WebMentions
- [ ] CRUD
- [ ] Bookmarklets
- [ ] Categories
- [ ] ActivityPub
- [ ] Syndication (FAWM?, Archive.org, Bandcamp?, indieweb news)
- [ ] Payments

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

- render responses (https://indieweb.org/responses), and return in feed
    - use bleach.clean (better: https://nh3.readthedocs.io/en/latest/)
    - do more work to populate a summary ,specially for websites without an h-entry

- private/draft

- webmention moderation
- replies to places that don't receive webmentions?
- move p-note to env
- private webmentions

- move get_entry to robida.helpers
- move relmeauth.api to auth.api
    - logout should send to homepage
    - add login/logout to header, showing logged-in name, picture
    - add indiauth provider
        - remember to add h-app
- on auth.html, ask for confirmation on giving refresh token and the expiration time of the access token
- index should be hcard

/bookmarklet blueprint
- Gives Bookmarkelt with token pre-filled if logged in
- Used for like/bookmark/repost/reply/song

- move db.execute out of API?
- index should point to tags on veganism/indieweb, etc?
- https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/
- https://chatgpt.com/c/aa0c1dc8-03e7-40e7-91dd-7cc6708f23d6
- if category is URL, convert to hcard for people tagging
- likes and replies by logging in with URL in my website
    - if the website supports micropub we could even post to it (repost? like?)
