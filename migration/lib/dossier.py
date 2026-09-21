import json,os,re,sqlite3,sys
sys.path.insert(0,os.environ["SCR"])
from resolve import resolve, pdf_pages, pdf_text
from norm import edition, edition_from_comment
from clean import *
LIB=os.path.expanduser("~/Calibre Library")
d=json.load(open(os.environ["SCR"]+"/sweep.json"))
db=sqlite3.connect(LIB+"/metadata.db")
Q="""select b.id,b.title,b.author_sort,b.path||'/'||dd.name||'.'||lower(dd.format),
 substr(b.pubdate,1,4),(select val from identifiers i where i.book=b.id and i.type='isbn'),
 (select s.name from books_series_link bs join series s on s.id=bs.series where bs.book=b.id),
 (select p.name from books_publishers_link bp join publishers p on p.id=bp.publisher where bp.book=b.id),
 (select text from comments c where c.book=b.id),
 (select group_concat(a.name,'|') from books_authors_link bal join authors a on a.id=bal.author where bal.book=b.id)
 from books b join data dd on dd.book=b.id order by b.id"""
INITIAL=re.compile(r"^[A-Z]\.?$")
def ambiguous_name(n):
    n=str(n)
    if "," in n: return False
    toks=[t for t in n.split() if not INITIAL.match(t)]
    if len(toks)<3: return False
    return not any(t.lower().strip(".") in PARTICLES for t in toks)

out=[]
for row in db.execute(Q):
    bid,ctitle,asort,rel,cyear,isbn,cser,cpub,ccom,cauth=row
    path=os.path.join(LIB,rel)
    ext=d.get(isbn,{}) if isbn else {}
    txt=pdf_text(path) if os.path.exists(path) else ""
    tc={}
    for s in ext:
        if not ext[s].get("hit"): continue
        t=strip_edition_tail(join_subtitle(unescape(ext[s].get("title")),unescape(ext[s].get("subtitle"))))
        if t and is_sentence_case(t): continue
        tc[s]=t
    tc["calibre"]=ctitle
    title,tsrc,tag,tcon=resolve("title",tc)
    ac={s:[unescape(x) for x in (ext[s].get("authors") or [])] for s in ext if ext[s].get("hit")}
    if asort: ac["calibre"]=[x.strip() for x in re.split(r"[&;]",asort) if x.strip()]
    au,asrc,aag,_=resolve("authors",ac)
    creators=[split_name(x) for x in (au or [])]
    amb=[n for n in (au or []) if ambiguous_name(n)]
    yc={s:ext[s].get("year") for s in ext if ext[s].get("hit")}
    py=year_from_pdf(txt)
    if py: yc["pdf"]=py
    if cyear and cyear!="0101": yc["calibre"]=cyear
    # self-published notes: the user's curated year beats a scanned copyright line
    if not ext and cyear and cyear!="0101": yc.pop("pdf",None)
    year,ysrc,yag,ycon=resolve("year",yc)
    ed_c={}
    for s in ("k10plus","openlibrary","loc"):
        if ext.get(s,{}).get("hit"):
            n,_=edition(ext[s].get("edition"))
            if n: ed_c[s]=n
    ec=edition_from_comment(ccom)
    if ec: ed_c["calibre_comment"]=ec
    ed,edsrc,_,edcon=resolve("edition",ed_c)
    sc={s:clean_series(ext[s].get("series")) for s in ext if ext[s].get("hit")}
    sc["calibre"]=clean_series(cser)
    ser,ssrc,_,_=resolve("series",sc)
    pc={s:clean_place(ext[s].get("place")) for s in ext if ext[s].get("hit")}
    place,_,_,_=resolve("place",pc)
    pub_c={s:ext[s].get("publisher") for s in ext if ext[s].get("hit")}; pub_c["calibre"]=cpub
    pub,pubsrc,_,pubcon=resolve("publisher",pub_c)
    abs_ok=any(ext.get(s,{}).get("abstract") for s in ("gb","k10plus","crossref"))
    flags=[]
    if not ext: flags.append("no-external-source")
    def _n(x): return re.sub(r"[^a-z0-9]","",str(x).lower())
    real_tcon=[(s,v) for s,v in tcon
               if not (_n(v).startswith(_n(title)) or _n(title).startswith(_n(v)))]
    if real_tcon: flags.append("title-conflict")
    if ycon and yag<2: flags.append("year-unconfirmed")
    if edcon: flags.append("edition-conflict")
    if amb: flags.append("name-split")
    if not creators: flags.append("no-authors")
    out.append(dict(calibre_id=bid,path=path,isbn=isbn,title=title,title_src=tsrc,
        creators=creators,authors_src=asrc,year=year,year_src=ysrc,edition=ed,edition_src=edsrc,
        series=ser,place=place,publisher=pub,pages=pdf_pages(path) if os.path.exists(path) else None,
        abstract_available=abs_ok,calibre_comment=ccom,flags=flags,
        n_sources=sum(1 for s in ext if ext[s].get("hit"))))
json.dump(out,open(os.environ["SCR"]+"/dossiers.json","w"),indent=1)
print("books:",len(out))
