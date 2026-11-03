"""Read-only local evidence collector; Python standard library only."""
import hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    data={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version.split()[0],'platform':platform.platform(),'root':str(ROOT),'files':{},'evidence':{}}
    for rel in ['docs/CHARTER.md','docs/DECISIONS.md','docs/AUDIT_M.md','docs/PROGRAM.md','docs/ROADMAP.md','requirements.txt','pyproject.toml']:
        p=ROOT/rel
        data['files'][rel]={'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}
    for pattern in ['**/verify_report*.json','**/runs.csv','**/quantbist_*.zip']:
        data['evidence'][pattern]=[str(p.relative_to(ROOT)) for p in ROOT.glob(pattern) if p.is_file() and not set(p.relative_to(ROOT).parts).intersection({'.git','.venv','venv'})][:30]
    dest=ROOT/'docs'/'PC_AUDIT_M_LOCAL.json'
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Denetim raporu:',dest)
    print('Bulunan kanıt sayıları:',{k:len(v) for k,v in data['evidence'].items()})
if __name__=='__main__':main()
