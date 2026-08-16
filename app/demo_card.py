"""The animated worked example shown beside the landing page copy.

It replays the product in miniature: a question is typed, the SQL the tool
would generate appears, then the answer draws itself. It is a self-contained
HTML component — static content, no database access — so the landing page stays
instant to load.
"""

import streamlit as st
import streamlit.components.v1 as components

QUESTION = "Which category sells the most?"
SQL = "SELECT category, SUM(price) AS total\nFROM orders GROUP BY category"
BARS = [54, 41, 32, 21, 13]          # relative heights, tallest first
CAPTION = "bed_bath_table leads with £11,245"

HEIGHT = 300

_HTML = f"""
<!doctype html>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500&family=JetBrains+Mono:wght@400&display=swap');
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: transparent; font-family: 'Manrope', sans-serif; }}
.card {{
  background: #1E1C19; border: 1px solid #2E2A25; border-radius: 12px;
  padding: 16px 18px; opacity: 0; transition: opacity .7s ease;
}}
.card.on {{ opacity: 1; }}
.dots {{ display: flex; gap: 5px; margin-bottom: 12px; }}
.dot {{ width: 6px; height: 6px; border-radius: 50%; background: #3A352E; }}
.ask {{
  background: #141311; border: 1px solid #2A2621; border-radius: 7px;
  padding: 9px 11px; min-height: 34px; font-size: 12.5px; color: #E4DED2;
}}
.cursor {{
  display: inline-block; width: 6px; height: 13px; background: #D9C7A3;
  vertical-align: -2px; animation: blink 1s steps(2) infinite;
}}
@keyframes blink {{ 0%,50% {{ opacity: 1 }} 51%,100% {{ opacity: 0 }} }}
.sql {{
  font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.65;
  color: #8FB89E; margin-top: 12px; white-space: pre; opacity: 0;
  transition: opacity .5s ease;
}}
.chart {{ margin-top: 14px; opacity: 0; transition: opacity .5s ease; }}
.bars {{ display: flex; align-items: flex-end; gap: 7px; height: 60px; }}
.bar {{
  flex: 1; height: 0; border-radius: 3px; background: #D9C7A3;
  transition: height .7s cubic-bezier(.22,.61,.36,1);
}}
.bar:nth-child(3), .bar:nth-child(4) {{ background: #8C7F66; }}
.bar:nth-child(5) {{ background: #5C5548; }}
.caption {{ font-size: 11px; color: #A79F90; margin-top: 10px; }}
.on {{ opacity: 1; }}
</style>

<div class="card" id="card">
  <div class="dots"><i class="dot"></i><i class="dot"></i><i class="dot"></i></div>
  <div class="ask"><span id="q"></span><span class="cursor" id="cursor"></span></div>
  <div class="sql" id="sql">{SQL}</div>
  <div class="chart" id="chart">
    <div class="bars">
      {"".join(f'<div class="bar" data-h="{h}"></div>' for h in BARS)}
    </div>
    <div class="caption">{CAPTION}</div>
  </div>
</div>

<script>
const QUESTION = {QUESTION!r};
const card = document.getElementById('card'), q = document.getElementById('q'),
      cursor = document.getElementById('cursor'), sql = document.getElementById('sql'),
      chart = document.getElementById('chart'), bars = document.querySelectorAll('.bar');
let timers = [], typing = null;
const later = (fn, ms) => timers.push(setTimeout(fn, ms));

function play() {{
  timers.forEach(clearTimeout); timers = []; if (typing) clearInterval(typing);
  card.classList.add('on');
  q.textContent = ''; cursor.style.display = 'inline-block';
  sql.classList.remove('on'); chart.classList.remove('on');
  bars.forEach(b => b.style.height = '0px');

  let i = 0;
  typing = setInterval(() => {{
    q.textContent = QUESTION.slice(0, ++i);
    if (i < QUESTION.length) return;
    clearInterval(typing);
    later(() => {{ cursor.style.display = 'none'; sql.classList.add('on'); }}, 400);
    later(() => {{
      chart.classList.add('on');
      bars.forEach((b, n) => later(() => b.style.height = b.dataset.h + 'px', n * 90));
    }}, 1100);
    later(() => card.classList.remove('on'), 7600);   // hold, then fade out
    later(play, 8500);                                 // and replay
  }}, 32);
}}
// The card fades in with the buttons; typing starts once it is on screen,
// otherwise the whole animation would play behind a transparent iframe.
card.classList.add('on');
setTimeout(play, 2000);
</script>
"""


def render() -> None:
    components.html(_HTML, height=HEIGHT)
