import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent   # docs/gap-study-4 (REPORT.md)
WORDS=r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen|none)\b"
def claim_lines(text=None):
    text = text if text is not None else (ROOT/"REPORT.md").read_text()
    out=[]; code=False
    for i,l in enumerate(text.split("\n"),1):
        if l.startswith("```"): code=not code; continue
        if code or l.startswith("|") or l.startswith("#"): continue
        bare=re.sub(r"`[^`]*`","",l)
        bare=re.sub(r"^\s*\d+\.\s","",bare)            # list numbering
        bare=re.sub(r"[Ss]ections? \d(?:\.\d)?","",bare)
        bare=re.sub(r"Table \d\.\d","",bare)
        bare=re.sub(r"Fable 5\.2|round 4|Round 4|RNA-seq","",bare)
        if re.search(r"\d",bare) or re.search(WORDS,bare,re.I): out.append((i,l))
    return out
if __name__=="__main__":
    for i,l in claim_lines(): print(i,l[:230])
