# Discord Bot Design Doc — BeatLeader Integration

## Command Reference (Discord slash-commands)

> **Formatting key**  
> **Summary** — what the command does  
> **Permissions** — who can run it  
> **Parameters** — with blurbs, types, validation  
> **Returns** — what your bot replies with  
> **BeatLeader API** — which BL call(s) you’ll hit and how parameters map

---

### Tournament

#### `/tournament create {name}`

**Summary**: Create an empty tournament container.  
**Permissions**: Organizer role.  
**Parameters**

- `name` _(string, required)_ — Human-friendly name; must be unique among active tournaments.
    

**Returns**

- `id` _(string)_ — New tournament ID (UUID).
    
- `tournament` — Echo of created object (id, name, status=`draft`).
    

**BeatLeader API**

- None. This is your bot’s own storage.
    

---

#### `/tournament get {id}`

**Summary**: Fetch a tournament by ID.  
**Permissions**: Any user.  
**Parameters**

- `id` _(string, required)_ — Tournament ID.
    

**Returns**

- `tournament` — Name, maps, registered players, schedule/status.
    

**BeatLeader API**

- None at call time. (When rendering, you may **decorate** map rows with BeatLeader leaderboard titles/links via a lightweight leaderboards lookup.)
    

---

#### `/tournament list`

**Summary**: List current tournaments (compact).  
**Permissions**: Any user.  
**Parameters**: none.  
**Returns**

- Array of `{ id, name, mapCount, playerCount, status }` (paginate if needed).
    

**BeatLeader API**

- None.
    

---

#### `/tournament update {id} {newName}`

**Summary**: Rename a tournament.  
**Permissions**: Organizer role.  
**Parameters**

- `id` _(string, required)_ — Tournament ID.
    
- `newName` _(string, required)_ — New unique name.
    

**Returns**

- `tournament` — Updated object.
    

**BeatLeader API**

- None.
    

---

#### `/tournament delete {id}`

**Summary**: Delete a tournament (soft-delete recommended).  
**Permissions**: Organizer role.  
**Parameters**

- `id` _(string, required)_ — Tournament ID.
    

**Returns**

- `success` _(boolean)_
    

**BeatLeader API**

- None.
    

---

#### `/tournament addMap {id} {mapId} {mapDiff} {mapMode}`

**Summary**: Attach a BeatLeader leaderboard (map+diff+mode) to a tournament.  
**Permissions**: Organizer role.  
**Parameters**

- `id` _(string, required)_ — Tournament ID.
    
- `mapId` _(string, required)_ — **Beat Saber song hash** (40-char SHA1 hex). (If you have a BeatSaver key, resolve to hash via BeatSaver API, then use hash for BeatLeader.)
    
- `mapDiff` _(string, required)_ — Difficulty label (e.g., `Easy|Normal|Hard|Expert|ExpertPlus`) or BL difficulty enum.
    
- `mapMode` _(string, required)_ — Game mode as known by BL (e.g., `Standard`, `OneSaber`, `NoArrows`, etc.).
    

**Returns**

- `success` _(boolean)_
    
- `map` — Stored tournament map record (including resolved `leaderboardId` if available).
    

**BeatLeader API**

- **Leaderboards by hash**: Resolve the leaderboard using **(hash + mode + difficulty)**. (See wrapper example for by-hash lookups.) [GitHub](https://github.com/Daanniello/BeatLeaderLib)
    
- If you started from a BeatSaver key: use **BeatSaver API** to fetch the hash, then BL by-hash. [api.beatsaver.com](https://api.beatsaver.com/docs/?utm_source=chatgpt.com)
    

---

#### `/tournament addPlaylist {id} {file}` _(stretch)_

**Summary**: Bulk-add maps from a `.bplist` file.  
**Permissions**: Organizer role.  
**Parameters**

- `id` _(string, required)_ — Tournament ID.
    
- `file` _(.bplist, required)_ — Standard Beat Saber playlist JSON.
    

**Returns**

- `successes` — List of `{ mapHash, accepted: boolean, reason? }`.
    

**BeatLeader API**

- BL doesn’t import playlists; **parse `.bplist` locally**, extract each map’s **hash or key**, then resolve BeatLeader leaderboards by hash as above. [bsmg.wiki](https://bsmg.wiki/faq/?utm_source=chatgpt.com)
    

---

#### `/tournament removeMap {id} {map}`

**Summary**: Remove a map from a tournament.  
**Permissions**: Organizer role.  
**Parameters**

- `id` _(string, required)_ — Tournament ID.
    
- `map` _(string, required)_ — Map identifier in your tournament (e.g., stored `leaderboardId` or the hash+mode+diff tuple).
    

**Returns**

- `success` _(boolean)_
    

**BeatLeader API**

- None.
    

---

#### `/tournament register {tournament}`

**Summary**: Add the calling user to a tournament’s player list if their Discord is linked to a BeatLeader profile.  
**Permissions**: Any user.  
**Parameters**

- `tournament` _(string, required)_ — Tournament name or ID.
    

**Returns**

- `success` _(boolean)_
    
- `reason` _(string, optional)_ — e.g., “Profile not linked.”
    

**BeatLeader API**

- **Players**: On first use, the user should have run `/profile register` to link Discord→BeatLeader `playerId`. Then only your DB is touched here. (Player data/validation can be rechecked via Players endpoint.) [api.beatleader.xyz](https://api.beatleader.xyz/swagger/index.html?utm_source=chatgpt.com)
    

---

#### `/tournament withdraw {tournament}`

**Summary**: Remove the calling user from a tournament’s player list.  
**Permissions**: Any user.  
**Parameters**

- `tournament` _(string, required)_ — Tournament name or ID.
    

**Returns**

- `success` _(boolean)_
    

**BeatLeader API**

- None.
    

---

#### `/tournament start {name} {startDate} {endDate}`

**Summary**: Set schedule and announcement channel for a tournament; bot will announce on start and compute winners on end.  
**Permissions**: Organizer role.  
**Parameters**

- `name` _(string, required)_ — Tournament name.
    
- `startDate` _(Discord timestamp string, required)_ — e.g., `<t:1758812400:f>`; store also as ISO8601.
    
- `endDate` _(Discord timestamp string, required)_ — Same format; must be after start.
    

**Returns**

- Confirmation that the tournament was scheduled.
    

**BeatLeader API (at runtime)**

- **Start announcement**: Build map list with **leaderboard links/titles** using leaderboards lookups. [api.beatleader.xyz](https://api.beatleader.xyz/swagger/index.html?utm_source=chatgpt.com)
    
- **End processing**: For each `(playerId, leaderboardId)` pair, fetch the player’s **best score** on that leaderboard and aggregate rankings. (Supported under Scores/Leaderboards categories.) [api.beatleader.xyz](https://api.beatleader.xyz/swagger/index.html?utm_source=chatgpt.com)
    
- **Optional live board**: Either **poll hourly** or consume **WebSocket play feed** and filter by participating players+leaderboards. [NuGet](https://www.nuget.org/packages/BeatLeaderLib?utm_source=chatgpt.com)
    

---

### Profile

#### `/profile register {url}`

**Summary**: Link a Discord user to a BeatLeader player profile.  
**Permissions**: Any user (self-service).  
**Parameters**

- `url` _(string, required)_ — BeatLeader profile link (e.g., `https://beatleader.com/u/313429`). Parse the numeric BL `playerId` from `/u/{id}`.
    

**Returns**

- `success` _(boolean)_
    
- `profile` — Stored linkage `{ discordId, beatleaderId, profileUrl }`.
    

**BeatLeader API**

- **Players**: Optionally call Players to verify the ID exists / fetch display name & avatar for display. (BeatLeader’s API lists Players category in Swagger.) [api.beatleader.xyz](https://api.beatleader.xyz/swagger/index.html?utm_source=chatgpt.com)
    
- Identity note: BeatLeader profiles are tied to a platform ID (Steam/Oculus/etc.). [beatleader.com](https://beatleader.com/privacy?utm_source=chatgpt.com)
    

---

#### `/profile delete`

**Summary**: Unlink a Discord user from BeatLeader.  
**Permissions**: Any user (self-service).  
**Parameters**: none.  
**Returns**

- `success` _(boolean)_
    

**BeatLeader API**

- None (local unlink).
    

---

#### `/profile display` _(optional)_

**Summary**: Show a user’s BeatLeader profile summary.  
**Permissions**: Any user.  
**Parameters**: none (use caller), or accept `@user`.  
**Returns**

- `profile` — Nicely formatted embed (avatar, name, country, rank, PP, etc.).
    

**BeatLeader API**

- **Players**: Fetch player summary for display. [api.beatleader.xyz](https://api.beatleader.xyz/swagger/index.html?utm_source=chatgpt.com)
    

---

### completedTournament

#### `/completedTournament {id}`

**Summary**: Show results for a finished tournament.  
**Permissions**: Any user.  
**Parameters**

- `id` _(string, required)_ — Completed tournament ID.
    

**Returns**

- `completedTournament` — Name, dates, maps, standings, winner, linkified map list.
    

**BeatLeader API**

- None at request time (data is archived in your DB). Optionally re-link map leaderboard titles via BL.
    

---

#### `/completedTournament list`

**Summary**: List previous tournaments (compact).  
**Permissions**: Any user.  
**Parameters**: none.  
**Returns**

- Array of `{ id, name, endedAt, winnerDisplayName }`.
    

**BeatLeader API**

- None.
    

---

#### `/completedTournament search {query}`

**Summary**: Search archived tournaments.  
**Permissions**: Any user.  
**Parameters**

- `query` _(string, required)_ — Search across name/description/winner.
    

**Returns**

- Matching `completedTournament` items.
    

**BeatLeader API**

- None.
    

---

#### `/completedTournament delete {id}`

**Summary**: Delete an archived tournament (admin only).  
**Permissions**: Organizer role.  
**Parameters**

- `id` _(string, required)_ — Completed tournament ID.
    

**Returns**

- `success` _(boolean)_
    

**BeatLeader API**

- None.
    

---

## JSON Data Structures

{
  "id": "uuid",
  "name": "string",
  "maps": [
    {
      "mapHash": "string",
      "mapMode": "string",
      "mapDiff": "string",
      "leaderboardId": "string",
      "title": "string",
      "blUrl": "string"
    }
  ],
  "players": [
    {
      "discordId": "string",
      "beatleaderId": "string",
      "displayName": "string",
      "scores": [
        {
          "leaderboardId": "string",
          "rawScore": 0,
          "accuracy": 0.0,
          "pp": 0.0,
          "rankOnMap": 0,
          "replayUrl": "string"
        }
      ],
      "totalScore": 0,
      "totalPP": 0.0
    }
  ],
  "leaderboard": [
    {
      "rank": 1,
      "beatleaderId": "string",
      "discordId": "string",
      "displayName": "string",
      "totalScore": 0,
      "totalPP": 0.0
    }
  ],
  "winner": {
    "beatleaderId": "string",
    "discordId": "string",
    "displayName": "string"
  },
  "startedAt": "ISO8601",
  "endedAt": "ISO8601",
  "announcementMessageId": "string",
  "resultsMessageId": "string",
  "createdAt": "ISO8601"
}
