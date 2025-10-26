import os, threading, time, datetime
from sqlalchemy import create_engine, text

URL=os.getenv("DATABASE_URL","sqlite:///./app.db")
PG=URL.startswith("postgres")
E=create_engine(URL, future=True)

def _w(f,s): print(s); f.write(s+"\n")

def _prep_nr(c):
    c.execute(text("drop table if exists t_nr"))
    c.execute(text("create table t_nr(id int primary key, v int)"))
    c.execute(text("insert into t_nr(id,v) values (1,150)"))

def _prep_ph(c):
    c.execute(text("drop table if exists t_ph"))
    if PG: c.execute(text("create table t_ph(id serial primary key, tag int)"))
    else: c.execute(text("create table t_ph(id integer primary key autoincrement, tag int)"))
    c.execute(text("insert into t_ph(tag) values (1)"))

def _prep_ws(c):
    c.execute(text("drop table if exists oncall"))
    c.execute(text("create table oncall(id int primary key, working bool)"))
    c.execute(text("insert into oncall(id,working) values (1,true)"))
    c.execute(text("insert into oncall(id,working) values (2,true)"))

def _engine(level=None):
    if level and PG: return create_engine(URL, future=True, isolation_level=level)
    return create_engine(URL, future=True)

def dirty_read(f):
    _w(f,"== DIRTY READ ==")
    if not PG:
        _w(f,"SKIP vendor"); return "SKIP"
    with E.begin() as c: _prep_nr(c)
    A=_engine("READ COMMITTED")
    with A.connect() as t1, A.connect() as t2:
        x=t1.begin(); t1.execute(text("update t_nr set v=200 where id=1"))
        y=t2.begin(); r=t2.execute(text("select v from t_nr where id=1")).scalar(); y.commit()
        x.rollback()
    _w(f,f"T2@RC read={r}")
    with E.begin() as c: cur=c.execute(text("select v from t_nr where id=1")).scalar()
    _w(f,f"after_rollback={cur}")
    ok=(r==150 and cur==150)
    _w(f,"PASS" if ok else "FAIL")
    return "PASS" if ok else "FAIL"

def nonrepeat_rc(f):
    _w(f,"== NON-REPEATABLE READ @ READ COMMITTED ==")
    with E.begin() as c: _prep_nr(c)
    A=_engine("READ COMMITTED")
    with A.connect() as a, A.connect() as b:
        ta=a.begin(); r1=a.execute(text("select v from t_nr where id=1")).scalar()
        def w(): 
            with b.begin() as tb: b.execute(text("update t_nr set v=250 where id=1"))
        t=threading.Thread(target=w); t.start(); t.join()
        r2=a.execute(text("select v from t_nr where id=1")).scalar(); ta.commit()
    _w(f,f"first={r1} second={r2}")
    ok=(r1!=r2 and r1==150 and r2==250)
    _w(f,"PASS" if ok else "FAIL")
    return "PASS" if ok else "FAIL"

def nonrepeat_rr(f):
    _w(f,"== NO NON-REPEATABLE READ @ REPEATABLE READ ==")
    if not PG:
        _w(f,"SKIP vendor"); return "SKIP"
    with E.begin() as c: _prep_nr(c)
    A=_engine("REPEATABLE READ"); B=_engine("READ COMMITTED")
    with A.connect() as a, B.connect() as b:
        ta=a.begin(); r1=a.execute(text("select v from t_nr where id=1")).scalar()
        def w():
            time.sleep(0.2)

            with b.begin() as tb: b.execute(text("update t_nr set v=300 where id=1"))
        t=threading.Thread(target=w); t.start(); t.join()
        r2=a.execute(text("select v from t_nr where id=1")).scalar(); ta.commit()
    _w(f,f"first={r1} second={r2}")
    ok=(r1==150 and r2==150)
    _w(f,"PASS" if ok else "FAIL")
    return "PASS" if ok else "FAIL"

def phantom_rc(f):
    _w(f,"== PHANTOM @ READ COMMITTED ==")
    with E.begin() as c: _prep_ph(c)
    A=_engine("READ COMMITTED")
    with A.connect() as a, A.connect() as b:
        ta=a.begin(); c1=a.execute(text("select count(*) from t_ph where tag=1")).scalar()
        def w():
            with b.begin() as tb: b.execute(text("insert into t_ph(tag) values (1)"))
        t=threading.Thread(target=w); t.start(); t.join()
        c2=a.execute(text("select count(*) from t_ph where tag=1")).scalar(); ta.commit()
    _w(f,f"first={c1} second={c2}")
    ok=(c1==1 and c2==2)
    _w(f,"PASS" if ok else "FAIL")
    return "PASS" if ok else "FAIL"

def phantom_rr(f):
    _w(f,"== NO PHANTOM @ REPEATABLE READ ==")
    if not PG:
        _w(f,"SKIP vendor"); return "SKIP"
    with E.begin() as c: _prep_ph(c)
    A=_engine("REPEATABLE READ"); B=_engine("READ COMMITTED")
    with A.connect() as a, B.connect() as b:
        ta=a.begin(); c1=a.execute(text("select count(*) from t_ph where tag=1")).scalar()
        def w():
            time.sleep(0.2)
            with b.begin() as tb: b.execute(text("insert into t_ph(tag) values (1)"))
        t=threading.Thread(target=w); t.start(); t.join()
        c2=a.execute(text("select count(*) from t_ph where tag=1")).scalar(); ta.commit()
    _w(f,f"first={c1} second={c2}")
    ok=(c1==1 and c2==1)
    _w(f,"PASS" if ok else "FAIL")
    return "PASS" if ok else "FAIL"

def serializable_ws(f):
    _w(f,"== WRITE SKEW: RR vs SERIALIZABLE ==")
    if not PG:
        _w(f,"SKIP vendor"); return "SKIP"
    with E.begin() as c: _prep_ws(c)
    def run(level):
        with E.begin() as c: c.execute(text("update oncall set working=true where id in (1,2)"))
        bar=threading.Barrier(2); res={}
        def tx(i,tag):
            eng=_engine(level); 
            with eng.connect() as x:
                t=x.begin(); n=x.execute(text("select count(*) from oncall where working=true")).scalar(); res[f"read_{tag}"]=n; bar.wait()
                x.execute(text("update oncall set working=false where id=:i"),{"i":i})
                try: t.commit(); res[f"commit_{tag}"]="commit"
                except Exception: res[f"commit_{tag}"]="rollback"
        t1=threading.Thread(target=tx,args=(1,"A"))
        t2=threading.Thread(target=tx,args=(2,"B"))
        t1.start(); t2.start(); t1.join(); t2.join()
        with E.begin() as c: res["final"]=c.execute(text("select count(*) from oncall where working=true")).scalar()
        return res
    r1=run("REPEATABLE READ")
    _w(f,f"RR reads={r1['read_A']},{r1['read_B']} commits={r1['commit_A']},{r1['commit_B']} final_working={r1['final']}")
    r2=run("SERIALIZABLE")
    _w(f,f"SER reads={r2['read_A']},{r2['read_B']} commits={r2['commit_A']},{r2['commit_B']} final_working={r2['final']}")
    ok_rr=(r1["final"] in (0,1,2)) and (r1["commit_A"]=="commit" and r1["commit_B"]=="commit")
    ok_ser=(r2["final"]>=1) and ({"commit","rollback"}=={r2["commit_A"],r2["commit_B"]})
    ok=ok_rr and ok_ser
    _w(f,"PASS" if ok else "FAIL")
    return "PASS" if ok else "FAIL"

def main():
    with open("log.txt","w",encoding="utf-8") as f:
        _w(f,"START "+datetime.datetime.utcnow().isoformat()+"Z")
        r=[]
        r.append(("dirty_read",dirty_read(f)))
        r.append(("nonrepeat_rc",nonrepeat_rc(f)))
        r.append(("nonrepeat_rr",nonrepeat_rr(f)))
        r.append(("phantom_rc",phantom_rc(f)))
        r.append(("phantom_rr",phantom_rr(f)))
        r.append(("serializable_ws",serializable_ws(f)))
        ok=sum(1 for _,x in r if x=="PASS")
        sk=sum(1 for _,x in r if x=="SKIP")
        fl=sum(1 for _,x in r if x=="FAIL")
        _w(f,f"SUMMARY pass={ok} skip={sk} fail={fl}")
        for k,v in r: _w(f,f"{k}: {v}")

if __name__=="__main__":
    main()