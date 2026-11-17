import os
from datetime import datetime, timezone
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='SplitScope | Private', page_icon='🏓', layout='wide')
st.markdown('''<style>.stApp{background:#0b1220;color:#eef2ff} [data-testid="stMetric"]{background:#182439;padding:14px;border-radius:12px} h1,h2,h3{color:#e7f8f0!important}</style>''',unsafe_allow_html=True)

def secret(k):
    return st.secrets.get(k, os.getenv(k,''))

BASE=str(secret('SUPABASE_URL')).rstrip('/')
KEY=str(secret('SUPABASE_SERVICE_ROLE_KEY'))
ADMIN=str(secret('ADMIN_EMAIL')).lower().strip()
if not BASE or not KEY or not ADMIN:
    st.error('App setup incomplete: configure SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and ADMIN_EMAIL in Streamlit secrets.'); st.stop()

def api(method, table, params=None, payload=None, prefer=None):
    headers={'apikey':KEY,'Authorization':f'Bearer {KEY}','Content-Type':'application/json'}
    if prefer: headers['Prefer']=prefer
    try:
        r=requests.request(method, f'{BASE}/rest/v1/{table}',headers=headers,params=params,json=payload,timeout=20)
        r.raise_for_status()
        return r.json() if r.content else []
    except requests.RequestException as exc:
        st.error(f'Database request failed: {exc}'); st.stop()

if not hasattr(st,'user') or not st.user.is_logged_in:
    st.title('🏓 SplitScope')
    st.write('Private table tennis analytics. Sign in with your approved Google account.')
    if st.button('Sign in with Google',type='primary'): st.login()
    st.stop()
email=str(st.user.get('email','')).lower().strip()
if not email or not bool(st.user.get('email_verified',False)):
    st.error('A verified email address is required.'); st.button('Sign out',on_click=st.logout); st.stop()
admin=email==ADMIN
if not admin:
    approved=api('GET','members',{'select':'email,active','email':f'eq.{email}','limit':'1'})
    if not approved or not approved[0]['active']:
        st.error('This account is not invited or its access was revoked. Ask the administrator to approve your email.')
        if st.button('Sign out'): st.logout()
        st.stop()

st.sidebar.title('🏓 SplitScope')
st.sidebar.caption(f'Signed in: {email}')
if st.sidebar.button('Sign out'): st.logout()
page=st.sidebar.radio('Navigation',['Dashboard','Match history','Head-to-head','Alerts']+(['Admin'] if admin else []))

@st.cache_data(ttl=45)
def load_data():
    hist=pd.DataFrame(api('GET','matches',{'select':'id,league,played_at,player_a,player_b,set1_a,set1_b,set2_a,set2_b','order':'played_at.desc','limit':'10000'}))
    upcoming=pd.DataFrame(api('GET','upcoming',{'select':'id,league,starts_at,player_a,player_b','order':'starts_at.asc','limit':'2000'}))
    return hist,upcoming

hist,upcoming=load_data()
for df,fields in [(hist,['league','played_at','player_a','player_b','set1_a','set1_b','set2_a','set2_b']), (upcoming,['league','starts_at','player_a','player_b'])]:
    for col in fields:
        if col not in df: df[col]=pd.Series(dtype='object')
if not hist.empty:
    for c in ['set1_a','set1_b','set2_a','set2_b']: hist[c]=pd.to_numeric(hist[c],errors='coerce')
    hist=hist.dropna(subset=['set1_a','set1_b','set2_a','set2_b'])
    hist=hist[(hist.set1_a!=hist.set1_b)&(hist.set2_a!=hist.set2_b)].copy()
    hist['split']=(hist.set1_a>hist.set1_b)!=(hist.set2_a>hist.set2_b)

def stats(df):
    n=len(df)
    return (round(100*df['split'].sum()/n,1),n) if n else (None,0)

def player_stats(name,n):
    data=hist[(hist.player_a==name)|(hist.player_b==name)].sort_values('played_at',ascending=False).head(n)
    return stats(data)

def h2h(a,b):
    return stats(hist[((hist.player_a==a)&(hist.player_b==b))|((hist.player_a==b)&(hist.player_b==a))])

st.title('🏓 SplitScope')
st.caption('Historical 1–1 first-two-set split analysis · Rankings are descriptive scores, not betting probabilities')
window=st.sidebar.selectbox('Recent matches per player',[10,20,50,100],index=1)
min_matches=st.sidebar.number_input('Minimum player sample size',1,100,10)
threshold=st.sidebar.slider('Alert ranking threshold',0,100,65)

if page=='Admin':
    st.subheader('Member access')
    st.info('Invite a member by approving their Google email here, then send them your app URL. No invitation email is sent automatically.')
    with st.form('member'):
        new_email=st.text_input('Member email').strip().lower()
        submitted=st.form_submit_button('Approve / restore access')
        if submitted:
            if '@' not in new_email or len(new_email)>254: st.error('Enter a valid email address.')
            else:
                api('POST','members',payload={'email':new_email,'active':True},prefer='resolution=merge-duplicates,return=minimal')
                st.success('Member approved. Share the website URL privately.')
    members=api('GET','members',{'select':'email,active','order':'email.asc'})
    if members:
        st.dataframe(pd.DataFrame(members),hide_index=True,use_container_width=True)
        target=st.selectbox('Select member to revoke', [m['email'] for m in members if m['active']]) if any(m['active'] for m in members) else None
        if target and st.button('Revoke access',type='primary'):
            api('PATCH','members',{'email':f'eq.{target}'},payload={'active':False},prefer='return=minimal'); st.rerun()
    st.divider(); st.subheader('Import match data')
    st.caption('Completed CSV: league,played_at,player_a,player_b,set1_a,set1_b,set2_a,set2_b. Upcoming CSV: league,starts_at,player_a,player_b. Use ISO date-times with timezone. Import does not deduplicate identical matches; include stable id values to upsert.')
    kind=st.selectbox('Data type',['Completed matches','Upcoming matches'])
    upload=st.file_uploader('Upload CSV',type=['csv'])
    if upload is not None:
        try:
            data=pd.read_csv(upload).fillna('')
            required=['league','played_at','player_a','player_b','set1_a','set1_b','set2_a','set2_b'] if kind=='Completed matches' else ['league','starts_at','player_a','player_b']
            missing=[c for c in required if c not in data]
            if missing: st.error('Missing columns: '+', '.join(missing))
            else:
                st.dataframe(data.head(10),hide_index=True)
                if st.button('Import rows'):
                    records=[]
                    for row in data.to_dict('records'):
                        item={k:row[k] for k in required}
                        if 'id' in row and str(row['id']).strip(): item['id']=str(row['id'])
                        if kind=='Completed matches':
                            for col in ['set1_a','set1_b','set2_a','set2_b']: item[col]=int(item[col])
                        records.append(item)
                    table='matches' if kind=='Completed matches' else 'upcoming'
                    for i in range(0,len(records),250): api('POST',table,payload=records[i:i+250],prefer='resolution=merge-duplicates,return=minimal')
                    load_data.clear(); st.success(f'Imported {len(records)} rows'); st.rerun()
        except (ValueError,TypeError) as e: st.error(f'Invalid CSV: {e}')
else:
    if page=='Dashboard':
        c1,c2,c3=st.columns(3)
        c1.metric('Completed matches',len(hist)); c2.metric('Upcoming matches',len(upcoming)); c3.metric('Historical split rate',f'{stats(hist)[0]}%' if len(hist) else '—')
        st.subheader('Upcoming matchup rankings')
        if upcoming.empty: st.info('No upcoming matches imported yet. Ask your administrator to add upcoming data.')
        else:
            rows=[]
            for m in upcoming.itertuples():
                a,na=player_stats(m.player_a,window); b,nb=player_stats(m.player_b,window); h,nh=h2h(m.player_a,m.player_b)
                score=round(.35*a+.35*b+.30*h,1) if a is not None and b is not None and h is not None else round((a+b)/2,1) if a is not None and b is not None else None
                eligible=na>=min_matches and nb>=min_matches
                rows.append({'League':m.league,'Starts':m.starts_at,'Player A':m.player_a,'Player B':m.player_b,'A split %':a,'A n':na,'B split %':b,'B n':nb,'H2H %':h,'H2H n':nh,'Ranking score':score,'Alert':bool(eligible and score is not None and score>=threshold)})
            ranked=pd.DataFrame(rows).sort_values('Ranking score',ascending=False,na_position='last')
            st.dataframe(ranked,hide_index=True,use_container_width=True)
            st.download_button('Download rankings CSV',ranked.to_csv(index=False),'rankings.csv','text/csv')
            st.caption('Ranking score uses 35% A, 35% B, 30% H2H when H2H exists; otherwise average of A and B. Small samples are not calibrated probabilities.')
    elif page=='Match history':
        st.subheader('Historical matches')
        if hist.empty: st.info('No completed match history imported yet.')
        else:
            leagues=['All']+sorted(hist.league.dropna().unique().tolist())
            league=st.selectbox('League',leagues)
            subset=hist if league=='All' else hist[hist.league==league]
            st.dataframe(subset,hide_index=True,use_container_width=True)
            st.download_button('Download history',subset.to_csv(index=False),'history.csv','text/csv')
    elif page=='Head-to-head':
        st.subheader('Head-to-head first-two-set splits')
        names=sorted(set(hist.player_a.dropna())|set(hist.player_b.dropna()))
        if len(names)<2: st.info('Import at least two players in completed match history.')
        else:
            a=st.selectbox('Player A',names,index=0)
            b=st.selectbox('Player B',names,index=1)
            if a==b: st.warning('Select two different players.')
            else:
                pct,n=h2h(a,b)
                st.metric('H2H split rate',f'{pct}%' if pct is not None else 'No meetings')
                st.caption(f'{n} completed meetings')
                st.dataframe(hist[((hist.player_a==a)&(hist.player_b==b))|((hist.player_a==b)&(hist.player_b==a))],hide_index=True,use_container_width=True)
    elif page=='Alerts':
        st.subheader('Alert rules')
        st.write(f'Flag matchups with a ranking score of at least **{threshold}** and at least **{min_matches}** historical matches per player.')
        st.info('Alerts are currently shown in the Dashboard table. Email, SMS, and background notifications are not enabled.')
