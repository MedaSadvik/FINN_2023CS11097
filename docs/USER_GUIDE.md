# FINN user guide

A walkthrough of every screen, step by step. Open https://finn-blush.vercel.app **on a phone** (the layout is built for a phone; a desktop browser shows the same thing in a narrow column).

A PDF copy with the same steps is in [FINN_User_Guide.pdf](FINN_User_Guide.pdf).

> **About the screenshots.** Today, Research and company pages are real FINN screens with real data. The signed-in screens (profile, connections, Call Sheets from your own network) were taken on a test copy of the site with invented people (Asha Verma, Dev Nair, Priya Iyer and others), so no real person's details appear. The screens look and behave the same as the live site.

**Contents**
1. [What FINN is](#what-finn-is)
2. [Today: what changed](#today-what-changed)
3. [Research: what management promised](#research-what-management-promised)
4. [Create an account](#create-an-account)
5. [Fill in your profile](#fill-in-your-profile)
6. [Add and accept connections](#add-and-accept-connections)
7. [Use your network](#use-your-network)
8. [Build research for a new company](#build-research-for-a-new-company)
9. [Good to know](#good-to-know)

---

## What FINN is

FINN is a briefing, not a dashboard. It has three tabs along the top.

| Tab | Question it answers |
|---|---|
| **Today** | What changed in the companies I follow, and who should I call about it? |
| **Research** | What did management promise on earnings calls, and did it happen? |
| **Network** | Which of my contacts used to work at these companies? |

The network is not a separate feature. It shows up as a **Call Sheet** under cards in Today and on every company page in Research.

---

## Today: what changed

### 1. Open Today
The first tab shows a short, ranked list of what changed in the last few days: results, deals, management changes, credit ratings and unusual trading. The newest, most important items come first. Each card quotes the company's own filing and links to it ("Open the filing").

![Today tab, signed out](guide/img/today_top.png)

### 2. Pick a time window
Choose **24 hours**, **3 days**, **7 days** or **14 days**. The heading shows the exact dates covered. Signed out, you see an invented network, as the strip at the top says.

![Longer window selected](guide/img/today_14d.png)

### 3. Set what counts as unusual
Tap **What counts as unusual**. Choose how big a volume spike (for example 2x the 20-day average) and how large a one-day price move (for example 5%) should raise an alert. Tick the kinds of filing you care about, then tap **Save**. These settings are saved on your device only.

![Alert rules](guide/img/today_settings.png)

### 4. Read a card
Cards come in a few kinds. A **management change** quotes the filing and names the person who left or joined.

![Management change card](guide/img/card_management.png)

A **results** card shows revenue, EBITDA, profit before tax and profit after tax, with the change against the previous quarter and the same quarter last year.

![Results card](guide/img/card_results.png)

An **alert** card says exactly which of your rules fired, for example "volume above 2x, price move beyond 5%".

![Alert card](guide/img/card_alert.png)

### 5. Open a Call Sheet
Tap the button under a card (for example **Who knows this company**). A sheet slides up listing the contacts who used to work there, what they did, who they overlapped with, and when you last spoke.

![Call Sheet](guide/img/call_sheet.png)

### 6. See who has a reason to hear from you
The strip near the top ("5 contacts have a reason to hear from you in this window") counts contacts connected to the companies that filed in your window. Tap it to see them.

![Contacts with a reason](guide/img/today_reason.png)

---

## Research: what management promised

### 7. Browse the companies
The **Research** tab lists the companies FINN has read, with how many promises it found in each. Tap one to open it.

![Research list](guide/img/research_list.png)

### 8. Search any listed company
Type a name or an NSE symbol (for example `asain paint`). FINN checks NSE's list of listed companies and suggests the closest match even if you misspell it. Companies not yet read say **Not built yet**.

![Search with a typo](guide/img/research_search.png)

### 9. Read a company page
The top of a page shows the company, its Call Sheet button, and chips that jump to each section (**Business**, **Promises**, **Words vs numbers**, **Quarters** and more). **Key numbers** shows the latest year at a glance.

![Company page](guide/img/company_top.png)

### 10. Read what the company does
**What the company does** gives a one-paragraph summary, then each business line with a quote from the latest call and the page it came from. Every line rests on words management actually said.

![What the company does](guide/img/company_business.png)

### 11. Read the bull case and bear case
**Bull case and bear case** lists reasons for and against, each with its quote and page. They come from the latest call only. FINN does not give a rating or a price target.

![Bull and bear case](guide/img/company_bullbear.png)

### 12. Check promised versus delivered
Every promise comes from an earnings call, with the exact quote highlighted, the call and page it came from, and a verdict:

- **Delivered**: the reported numbers meet the promise. Some are settled from a later call where management states the actual figure ("What they said later").
- **Missed**: they do not.
- **Pending**: the promised period has not finished (for example, "reported so far through FY27").
- **Can't check yet**: the quarterly tables cannot answer it. FINN says so rather than guessing.

The verdict is plain arithmetic on reported numbers, not an opinion from a model.

![Promises with verdicts](guide/img/company_promises.png)

### 13. Read the plain-language summary
A short summary says what the record adds up to: how many promises were checked, how many were delivered, and where the numbers and the promises disagree. Green **Good** and red **Watch** lines flag the findings.

![Summary](guide/img/company_narrative.png)

### 14. See the multi-year trend
Revenue and operating margin over several years, with a one-line reading under the chart.

![Trajectory](guide/img/company_trajectory.png)

### 15. Check the balance sheet
Borrowings against net worth, debt to equity, interest cover, the cash conversion cycle and debtor days. Each row shows the change against two years earlier.

![Balance sheet](guide/img/company_balance.png)

### 16. Check cash quality
Does reported profit turn into cash? The chart compares profit after tax with cash from operations for three years. Red bars mean cash going out.

![Cash quality](guide/img/company_cash.png)

### 17. Read the reported quarters
The last quarters of revenue, EBITDA, profit before tax and profit after tax, in rupees crore.

![Reported quarters](guide/img/company_quarters.png)

### 18. Ask who in your network knows the company
Tap **Who in your network knows this company** at the top of the page. The sheet lists your contacts with a past at this company. It is the same Call Sheet as in Today.

![Call Sheet on a company page](guide/img/company_call_sheet.png)

---

## Create an account

You only need an account for the Network tab and to build new companies. Today and Research work without one.

### 19. Open the Network tab signed out
Signed out, the Network tab shows an invented network so you can see how it works. Tap **Sign in** at the top right to use your own.

![Network tab signed out](guide/img/network_signed_out.png)

### 20. Choose sign in or create account
The form has two tabs. To make a new account, tap **Create account**.

![Sign in](guide/img/signin.png)

### 21. Create your account
Enter your name, a username, your email and a password (at least 8 characters). Your username is how other people find you: lowercase letters, numbers and underscore, and others type it exactly. There is no email confirmation step. You are signed in at once.

![Create account](guide/img/signup_form.png)

### 22. Land on your profile
After signing up you reach your profile. Your avatar (the circle with your initial) appears at the top right on every screen.

![New profile](guide/img/me_new.png)

---

## Fill in your profile

Your jobs and schools are what let FINN find overlaps. **Connections see them. Nobody else does.**

### 23. Save your name and headline
Edit your name and a one-line headline (for example "Portfolio Manager, Ashoka Capital"), then tap **Save**.

![Profile saved](guide/img/me_saved.png)

### 24. Add a job
Under **Career**, tap **Add a job**. Enter the company (pick a company FINN tracks to get overlaps, or type any name), your title, and the years. Leave **To year** blank if you still work there.

![Add a job form](guide/img/job_form.png)

### 25. See the job added
The job shows up in your career list. You can remove it any time.

![Job added](guide/img/job_added.png)

### 26. Add a school
Under **Education**, tap **Add a school** and fill in the same way.

![School added](guide/img/school_added.png)

---

## Add and accept connections

A connection is a two-way agreement. Until the other person accepts, you cannot see their career and they cannot see yours.

### 27. Open Network with no connections yet
Your own Network tab starts empty. Your username is shown ("You are @asha_verma") so you can share it. Below that is the box to add someone.

![Empty network](guide/img/network_empty.png)

### 28. Connect with a demo account (to try alone)
If you have nobody to connect with, type `demo_priya`, `demo_kabir` or `demo_meera` and tap **Send request**. These are invented people who accept at once.

![Typing a demo username](guide/img/connect_demo.png)

### 29. Connect with a real person
Type their exact username and tap **Send request**. A message confirms it was sent and that they need to accept.

![Request sent](guide/img/connect_request.png)

### 30. See your connections
Accepted connections appear under **Connections**, with their headline and career. Their jobs now count in your Call Sheets (marked "their profile"). Use **Remove** to end a connection.

![Connections](guide/img/connections_list.png)

### 31. Wait for an answer
Requests you sent show under **Waiting for an answer**. Tap **Cancel** to withdraw one.

![Waiting](guide/img/waiting.png)

### 32. Receive a request
When someone asks to connect with you, it shows under **Asked to connect with you**, with their name, headline and username. A note says what accepting does: it lets them see your jobs and schools, and lets you see theirs.

![Incoming request](guide/img/incoming.png)

### 33. Accept or decline
Tap **Accept** to connect or **Decline** to turn it down. A declined request is simply removed.

![Accepted](guide/img/accepted.png)

---

## Use your network

### 34. Load sample contacts
Want to try FINN before anyone accepts? Tap **Load sample contacts** at the bottom of the Network tab. FINN adds 120 invented people, with 50 close contacts you can scroll through. Tap **Remove sample contacts** in the same place to clear them.

![Sample contacts button](guide/img/sample_load.png)

![Sample contacts loaded](guide/img/sample_loaded.png)

### 35. Read "Worth a call"
At the top of **Your network**, FINN lists contacts who used to work at a company that just filed and whom you have not spoken to in six months or more. Each one says why now, when you last spoke, and a question to ask.

![Worth a call](guide/img/network_insights.png)

### 36. Read "Who knows what"
Further down, contacts are grouped by sector (IT services, semiconductors, energy and so on), counted from years spent at the companies FINN tracks. Tap a sector to see the people.

![Who knows what](guide/img/who_knows_what.png)

### 37. Open a contact's profile
Tap a name. The profile shows their role, when you last spoke (if you have set it), why they matter for each company you follow, their career and education.

![Contact profile](guide/img/person_top.png)

### 38. Record when you last spoke
Under the name, the **Last spoke** box takes a month and year. Pick one and tap **Save**. The profile, "Worth a call" and the draft email all use it. Contacts you made by connecting with a real person start blank, so set it here. Clear the box and save to remove it. Only you can see this date.

![Last spoke](guide/img/last_spoke.png)

### 39. Draft an email
Tap **Draft an email**. FINN writes a short, polite note that mentions how long it has been, the company in the news and their old role. You can edit the subject and message.

![Draft open](guide/img/draft_open.png)

### 40. Send it from your mail app
Tap **Open in mail app** to start the email in your own mail app, or **Copy** to paste it somewhere else. FINN does not hold their email address and sends nothing itself.

![Draft buttons](guide/img/draft_buttons.png)

---

## Build research for a new company

Signed-in users can ask FINN to read a company it has not read yet. This takes a few minutes and runs in the background.

### 41. Ask for a company
In Research, type the name or symbol of a listed company (for example `MARUTI`) and open it. If FINN has not read it yet, it says so and offers **Build research for MARUTI**. Tap it to start.

![Ask to build](guide/img/build_ask.png)

### 42. Wait while it builds
The page says what is happening ("Building research for TATASTEEL. Reading the earnings calls. This usually takes 3 to 6 minutes") and refreshes itself when ready. You can leave and come back.

![Building](guide/img/build_working.png)

### 43. Update a company when a new call is out
Research built on request is checked every evening. If the company has held a newer earnings call, its page says so ("A newer earnings call (Q2FY27) is out. This research uses calls up to Q1FY27.") and shows **Update TITAN with the new call**. It reads the calls with a model, takes a few minutes and counts toward the daily limit, like a first build. The old research stays on the page until the new one is ready. If there is no newer call, no button appears.

![Update offer](guide/img/update_offer.png)

### 44. Typed it wrong, or not listed?
If the symbol is not on NSE's list, FINN says so and suggests the closest listed companies ("Did you mean Titan Company Limited"). Tap one to continue, or **Search again**.

![No match](guide/img/company_notfound.png)

---

## Good to know

- **Draft label.** Research marked **Draft** was extracted by a test model and has not been checked as closely. Treat it as a preview.
- **"Can't check yet".** FINN shows this when a promise cannot be tested against the numbers it has. It never fills the gap with a guess.
- **Daily limit.** The free AI quota behind new builds and updates is shared. If it runs out, the build waits and FINN says so. A limited number of builds per person per day also applies.
- **Primary sources only.** Research uses earnings call transcripts, exchange filings and the annual tables. It does not use news.
- **Privacy.** Your jobs and schools are visible only to people you have accepted. The rules are enforced in the database, not just in the app, and are tested. The AI model never sees your network: Call Sheets, "Worth a call", "Who knows what" and the draft email are plain rules, not model output.
- **Nothing is sent for you.** FINN never emails anyone. It drafts; you press send.

### 45. Sign out
Tap your avatar at the top right to open your profile, scroll to the bottom and tap **Sign out**. You go back to the signed-out view with the invented network.

![Sign out](guide/img/sign_out.png)
