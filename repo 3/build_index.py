#!/usr/bin/env python3
"""Builds the front page, injecting the live Daily Docket rail."""
from pathlib import Path
ROOT = Path(__file__).parent
RAIL = (ROOT / "data" / "_rail.html").read_text()

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unforced Error — Cybersecurity, technology, and government</title>
<meta name="description" content="Reports and a daily docket on cybersecurity, technology, and government. Filings quoted, never summarized. Edited by Aiden Goldenberg.">
<meta property="og:title" content="Unforced Error">
<meta property="og:description" content="Cybersecurity, technology, and government — read from the filings themselves.">
<meta property="og:type" content="website">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/ue.css">
</head>
<body>

<div class="wire" aria-hidden="true">
  <div class="wire-track">
    <span><span class="tag">FTC</span>SECTION 5 REACHES DECEPTIVE AI OUTPUTS "EVEN WHEN" DONE TO COMPLY WITH STATE LAW — COMMENTS CLOSE JULY 31</span>
    <span><span class="tag">FCC</span>NG911 RELIABILITY RULES ADOPTED — EFFECTIVE AUGUST 10, 2026</span>
    <span><span class="tag">FCC</span>KNOW-YOUR-UPSTREAM-PROVIDER RULES PROPOSED FOR VOICE CARRIERS</span>
    <span><span class="tag">SEC</span>COMMISSION REOPENS SECURITY REQUIREMENTS FOR THE CONSOLIDATED AUDIT TRAIL</span>
    <span><span class="tag">DOCKET</span>5 PUBLISHED · 3 HELD, SOURCE UNREACHABLE · 12 SCREENED OUT</span>
    <span><span class="tag">FTC</span>SECTION 5 REACHES DECEPTIVE AI OUTPUTS "EVEN WHEN" DONE TO COMPLY WITH STATE LAW — COMMENTS CLOSE JULY 31</span>
    <span><span class="tag">FCC</span>NG911 RELIABILITY RULES ADOPTED — EFFECTIVE AUGUST 10, 2026</span>
    <span><span class="tag">FCC</span>KNOW-YOUR-UPSTREAM-PROVIDER RULES PROPOSED FOR VOICE CARRIERS</span>
    <span><span class="tag">SEC</span>COMMISSION REOPENS SECURITY REQUIREMENTS FOR THE CONSOLIDATED AUDIT TRAIL</span>
    <span><span class="tag">DOCKET</span>5 PUBLISHED · 3 HELD, SOURCE UNREACHABLE · 12 SCREENED OUT</span>
  </div>
</div>

<div class="dateline">
  <span>Vol. I — No. 001</span>
  <span class="mid" id="today">Read from the filings themselves</span>
  <span>Price: $0.00</span>
</div>

<header class="masthead">
  <a class="nameplate" href="index.html"><span class="g" data-t="Unforced Error">Unforced Error</span></a>
  <p class="tag">Cybersecurity · Technology · Government — <b>edited by Aiden Goldenberg</b></p>
</header>

<nav class="paper" aria-label="Sections">
  <a href="#reports">Reports</a>
  <a href="docket.html">The Docket</a>
  <a href="about.html">The Editor</a>
  <a href="house-rules.html">House Rules</a>
  <a href="#subscribe">Subscribe</a>
</nav>

<!-- SPLIT: reports left, live docket right -->
<div class="split">
  <main>
    <div class="secrule"><span class="secno">SEC.01</span><h2>Reports</h2><span class="secno">LATEST</span></div>

    <article style="margin-bottom:40px">
      <div class="eyebrow">Enforcement · FTC Docket C-4833</div>
      <h1 style="font-size:clamp(28px,3.9vw,44px);line-height:1.1;font-weight:700;letter-spacing:-.02em;margin-bottom:14px">
        <a href="reports/illuminate-ftc-order.html" style="text-decoration:none">The FTC just closed a case over a login that stayed active for three and a half years</a>
      </h1>
      <p style="font-size:20px;color:var(--ink-2);line-height:1.5;margin-bottom:18px">A security vendor warned the company in January 2020. The break-in came twenty-three months later, through an administrator account belonging to someone who had quit in April 2018. Nobody ever switched it off.</p>
      <div class="abyline">
        <span>By <a href="about.html">Aiden Goldenberg</a> · July 9, 2026 · 6 min</span>
        <span><a class="cred" href="checks/illuminate-ftc-order.html"><b>27 facts</b> · <i>7 cut</i> · sources verified</a></span>
      </div>
      <div class="lead">
        <div class="cols">
          <p>Illuminate Education makes cloud software that schools use to track attendance, grades, test scores, and learning disabilities. In a complaint the company neither admitted nor denied, the FTC accused it of failing to protect data on more than ten million students.</p>
          <p>The timeline is the story. An outside security firm graded the network a "C" in January 2020 and named the problems: weak account management, outdated software, weak passwords. The firm came back in February 2021 and found them unfixed.</p>
          <p>On December 27, 2021 someone logged in with credentials belonging to an administrator who had left the company in April 2018. They had twelve days inside before anyone noticed, and left with 787 database backups.</p>
          <p>What makes this worth reading isn't the breach. It's the order that closed it. For the next ten years Illuminate must use phishing-resistant MFA — the FTC explicitly forbids SMS codes — encrypt at rest and in transit, and cut off any departing employee's access within thirty days. <b>Read enough of these and a pattern appears: the remedy is a photograph of the failure.</b></p>
        </div>
        <p style="margin-top:18px"><a href="reports/illuminate-ftc-order.html" style="font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.1em;text-transform:uppercase;text-decoration:none;border-bottom:2px solid var(--green);padding-bottom:2px">Continue reading →</a></p>
      </div>
    </article>

    <div class="empty" style="margin-bottom:34px">
      <b>The next report is in progress.</b><br>
      Reports go up when the sourcing holds, not on a timer. The <a href="docket.html" style="border-bottom:1px solid var(--green);text-decoration:none">Daily Docket</a> updates every morning regardless — that's where the raw filings land the moment they're published.
    </div>

    <div class="secrule"><span class="secno">SEC.02</span><h2>What We Cover</h2><span class="secno">THREE BEATS</span></div>
    <div class="steps">
      <div class="step"><div class="n">01</div><h3>Enforcement</h3><p>Complaints, consent orders, and litigation releases from the FTC, SEC, and DOJ. The remedy is where an agency writes down what it actually expects.</p></div>
      <div class="step"><div class="n">02</div><h3>Rulemaking</h3><p>What the Federal Register published, who it binds, and when the clock starts. Read before the trade press summarizes it for you.</p></div>
      <div class="step"><div class="n">03</div><h3>Courts &amp; Advisories</h3><p>Filings, opinions, and CISA advisories. The documents, not the coverage of the documents.</p></div>
    </div>
  </main>

  {RAIL}
</div>

<!-- SUBSCRIBE -->
<div class="sub-wrap" id="subscribe">
  <div class="coupon">
    <span class="sc" aria-hidden="true">✂</span>
    <div class="ey">Clip &amp; Subscribe · The docket daily, reports when they land</div>
    <h2>One email. No noise.</h2>
    <p class="s">The morning docket, and every report as it publishes. Free, and always will be. No sponsors, no vendors, no ads.</p>
    <form name="subscribe" method="POST" data-netlify="true" netlify-honeypot="bot-field" id="subform">
      <input type="hidden" name="form-name" value="subscribe">
      <p style="display:none"><label>Leave blank: <input name="bot-field"></label></p>
      <input type="email" name="email" required placeholder="you@example.com" aria-label="Email address">
      <button type="submit">Subscribe</button>
    </form>
    <p class="fine">NO SPAM · WE NEVER SELL THE LIST · UNSUBSCRIBE ANYTIME</p>
    <p class="msg" id="formmsg" role="status"></p>
  </div>
</div>

<footer>
  <div class="foot">
    <span>© 2026 Unforced Error</span>
    <span><a href="about.html">Aiden Goldenberg, Editor</a> · <a href="house-rules.html">House Rules</a></span>
    <span>Primary sources only · Not legal advice</span>
  </div>
</footer>

<script>
(function(){{
  var d=new Date();
  var days=["SUNDAY","MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY"];
  var mo=["JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE","JULY","AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"];
  document.getElementById("today").textContent=days[d.getDay()]+", "+mo[d.getMonth()]+" "+d.getDate()+", "+d.getFullYear();
  var f=document.getElementById("subform"), msg=document.getElementById("formmsg");
  f.addEventListener("submit",function(e){{
    e.preventDefault();
    fetch("/",{{method:"POST",headers:{{"Content-Type":"application/x-www-form-urlencoded"}},
      body:new URLSearchParams(new FormData(f)).toString()}})
      .then(function(r){{ if(!r.ok) throw new Error("no");
        f.querySelector("button").textContent="SUBSCRIBED ✓";
        msg.style.color="var(--green)"; msg.textContent="You're on the list."; }})
      .catch(function(){{ msg.textContent="Signups aren't connected on this host yet. Your address was NOT saved."; }});
  }});
}})();
</script>
</body>
</html>
'''
(ROOT / "site" / "index.html").write_text(HTML)
print("index.html rebuilt with live docket rail")
