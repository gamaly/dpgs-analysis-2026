"""T7: review of merged human PRs by reviewer type (human / AI-only / automation-only / none).
Reads data/all_repos.csv (confidence high) and cache/<owner>__<repo>.json; run from the project root with python -I.
Writes docs/post/findings_tables/: t7_review_ai_by_year.csv, t7_review_ai_by_half_year.csv, t7_review_repo_spread.csv,
t7_review_concentration.csv, t7_ai_reviewers_by_year.csv. Classes: ai_only = no human reviewer, at least one AI agent reviewer;
automation_only = no human or AI reviewer, only bots (github-actions, mergify, ...); unreviewed = no review before merge."""
import json,os,re,collections,pandas as pd
src=open('scripts/03_aggregate.py',encoding='utf-8').read().split('\n')
s=next(i for i,l in enumerate(src) if l.startswith('DEP_BOTS')); e=next(i for i,l in enumerate(src) if l.startswith('def actor_class'))
ns={'re':re}; exec('\n'.join(src[s:e+6]),ns); actor_class=ns['actor_class']
ar=pd.read_csv('data/all_repos.csv'); ar=ar[ar.confidence=='high'].drop_duplicates('full_name')
rows=[];ai=collections.defaultdict(collections.Counter);miss=0;cap=0;tot=0
for fn in ar.full_name:
    p='cache/'+fn.replace('/','__')+'.json'
    if not os.path.exists(p): miss+=1; continue
    d=json.load(open(p,encoding='utf-8'))
    if d.get('status')!='ok': miss+=1; continue
    for pr in d['prs']:
        m=pr.get('mergedAt'); a=pr.get('author') or {}; au=a.get('login') or ''
        if not m or m<'2020' or not au or actor_class(au,a.get('__typename'))!='human': continue
        nodes=(pr.get('reviews') or {}).get('nodes') or []
        tot+=1; cap+=len(nodes)>=10
        rv=[r for r in nodes if (r.get('author') or {}).get('login') and r.get('submittedAt') and r['author']['login'].lower()!=au.lower() and r['submittedAt']<=m]
        y=int(m[:4])
        hum=any(actor_class(r['author']['login'],r['author'].get('__typename'))=='human' for r in rv)
        isai=any(actor_class(r['author']['login'],r['author'].get('__typename'))=='ai_agent' for r in rv)
        cl='a' if hum else ('b1' if isai else ('b2' if rv else 'c'))
        for r in rv:
            if actor_class(r['author']['login'],r['author'].get('__typename'))!='human': ai[y][r['author']['login']]+=1
        rows.append((fn,y,f"{y}H{1 if int(m[5:7])<=6 else 2}",cl))
df=pd.DataFrame(rows,columns=['repo','y','h','cl'])
print('repos',df.repo.nunique(),'missing',miss,'PRs',len(df),'cap share',round(cap/tot,3))
def tab(k):
    g=df.groupby([k,'cl']).size().unstack(fill_value=0)
    for c in ['a','b1','b2','c']:
        if c not in g: g[c]=0
    n=g.sum(axis=1); o=pd.DataFrame({k:g.index,'merged_human_prs':n.values,'share_human_reviewed':(g.a/n).round(4).values,'share_ai_only':(g.b1/n).round(4).values,'share_automation_only':(g.b2/n).round(4).values,'share_unreviewed':(g.c/n).round(4).values})
    return o
O='docs/post/findings_tables/'
y=tab('y'); y=y[(y.y>=2020)&(y.y<=2026)]; y.to_csv(O+'t7_review_ai_by_year.csv',index=False); print(y)
h=tab('h'); h=h[h.h>='2024H1']; h['partial']=h.h=='2026H2'; h.to_csv(O+'t7_review_ai_by_half_year.csv',index=False); print(h)
df['hr']=df.cl=='a'
def per(lo,hi):
    return df[(df.y>=lo)&(df.y<=hi)].groupby('repo').hr.agg(['size','mean'])
a=per(2023,2024); b=per(2025,2026); j=a.join(b,lsuffix='_p1',rsuffix='_p2',how='inner'); j=j[(j.size_p1>=20)&(j.size_p2>=20)]
j['change_pts']=((j.mean_p2-j.mean_p1)*100).round(1)
j.rename(columns={'size_p1':'n_2023_24','mean_p1':'human_share_2023_24','size_p2':'n_2025_26','mean_p2':'human_share_2025_26'}).round(4).to_csv(O+'t7_review_repo_spread.csv')
print('repos',len(j),'fell',(j.change_pts<-10).sum(),'within',(j.change_pts.abs()<=10).sum(),'rose',(j.change_pts>10).sum(),'median',j.change_pts.median())
un=df.assign(u=df.cl=='c').groupby(['repo','y']).u.sum().unstack(fill_value=0)
n=df.groupby(['repo','y']).size().unstack(fill_value=0); hs=df.groupby(['repo','y']).hr.mean().unstack()
inc=(un[2026]*4/3-un[2024]).sort_values(ascending=False)
t=pd.DataFrame({'unrev_2024':un[2024],'unrev_2026_annualised':(un[2026]*4/3).round(1),'increase':inc,'n_2024':n[2024],'n_2026':n[2026],'human_share_2024':hs[2024].round(3),'human_share_2026':hs[2026].round(3)}).loc[inc.index[:10]]
t.to_csv(O+'t7_review_concentration.csv'); print(t); print('total increase',round(inc.sum(),1),'top10',round(inc[:10].sum(),1))
rows=[]
for yy in range(2020,2027):
    for l,c in ai[yy].most_common(10): rows.append((yy,l,c))
pd.DataFrame(rows,columns=['year','reviewer_login','reviews']).to_csv(O+'t7_ai_reviewers_by_year.csv',index=False)
for yy in range(2023,2027): print(yy,ai[yy].most_common(10))
