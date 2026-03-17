# Problem Framing

## what's actually broken

i spent about 120 minutes talking to Ira before writing any code. called her up, shared my life story, tested corrections, pushed boundaries, deliberately contradicted myself. i wanted to understand what fails before deciding what to build.

the short version: Ira's short-term memory within a session is decent. she remembered my friends' names, where Friend 1's wedding was, that Friend 2 works at Marriott. the factual memory works. what doesn't work is everything that makes a companion feel like a companion.

### the conversation doesn't feel like a conversation

i gave Ira a detailed 2.5-minute introduction — childhood, cities, startups, career. her response: "accha theek hai, aur batao." that's it. no follow-up on anything specific. no curiosity. a friend would've grabbed onto something — the startup that got acquired, the city i grew up in, anything. Ira treated it as data ingestion and moved on.

worse, she pre-batches questions. i noticed she decides upfront what to ask, then goes through them in order regardless of what i say in between. i was talking about Gorakhpur and she jumped to "how was Dehradun?" — completely ignoring the active thread. later, i'd already said Deathly Hallows was my favorite Harry Potter movie. her next question: "what's your favorite Harry Potter movie?" 

she also can't take the lead. when i said "tum bolo" she responded with "kya hum aage baat kar sakte hain?" — a meta-statement about the conversation rather than actual content. a companion that can only respond but never initiate is not a companion, it felt more like a customer support bot with a friendly voice.

### corrections don't persist

this one's a dealbreaker. i explicitly told Ira three things: stop greeting me with "are tum phir se aa gaye," you should've asked about Gorakhpur not Dehradun, and don't ask those pre-batched questions. she acknowledged each one — "mujhe afsoos hai, agali baar dhyan rakhungi" — and then did the exact same thing on the next call. three times. this is worse than forgetting. it's performative acknowledgment with zero follow-through.

### contradiction detection doesn't exist

i deliberately told her i was born, raised, and lived my entire life in Bangalore — after spending 10 minutes talking about growing up in Gorakhpur and studying in Dehradun. she accepted it without blinking. when i pushed — "if i've always lived in Bangalore, how did i study in Dehradun?" — she just repeated both statements as independently true. no consistency check, no flag, nothing. user's verdict, my verdict: "it has completely broken down now."

### what actually worked

voice quality is good. extremely good. truly sota. short-term factual recall works. she correctly handled a name swap correction within the session. she knows Mahoba is in Bundelkhand. and she maintained romantic boundaries consistently across 5+ escalation attempts — warm but firm. these are great positives.

---

## what's product-critical

not every failure matters equally. i rank them by trust destruction velocity — how fast they make someone stop trusting the companion.

| priority | failure | why it's critical |
|---|---|---|
| P0 | fabricated recall | gaslighting. instant trust death. |
| P0 | cross-user memory leak | privacy violation. legal liability. |
| P0 | sensitive memory dumping | emotional harm. user shared something vulnerable and the system throws it back unprompted. |
| P1 | correction not persisted | "i already told you this" is the fastest way to make someone feel unheard. |
| P1 | direct recall miss | the system doesn't care enough to remember. |
| P2 | generic filler ("aur batao?") | feels scripted. the mask slips. |
| P2 | post-conflict amnesia | feels like talking to a stranger who forgot yesterday happened. |
| P3 | temporal hallucination | guessing the time/date. undermines factual credibility. |

the first three are non-negotiable. a companion that fabricates memories, leaks user data across profiles, or dumps intimate context in casual conversation is not shippable. i don't care how warm the voice sounds.

---

## what "best-in-class" actually means

best-in-class is not about sounding the most human or being the most expressive. it's about being reliably trustworthy while remaining warm.

a best-in-class companion:

1. **recalls directly** when it has the information. no hedging, no filler, no re-asking what it already knows.

2. **admits honestly** when it doesn't know. "yaar, ye mujhe yaad nahi hai, bata na?" is better than "tell me more about that!" — the first is honest warmth, the second is deflection wearing warmth as a costume.

3. **never fabricates.** silence is better than a lie. always.

4. **handles corrections as first-class operations.** supersession, not overwrite. old facts stay as history, new facts become current, entity disambiguation is explicit. "Spark mera rat nahi hai, hamster hai" should create two clean records, not a contradictory mess.

5. **respects sensitivity.** knows when to recall directly, when to summarize, when to ask before revealing, and when to stay silent. matches disclosure to conversational context.

6. **maintains continuity.** emotional context, conflict history, relationship evolution — they carry forward. no amnesiac resets between sessions.

7. **isolates perfectly.** user A's girlfriend's name never shows up in user B's session. ever.

### the numbers i'm targeting

| metric | target |
|---|---|
| critical honesty cases | 100% |
| multi-user isolation | 100% |
| fabricated memories | 0 |
| live-time hallucinations | 0 |
| direct recall success | 90%+ |
| correction success | 90%+ |
| relationship-state accuracy | 85%+ |


