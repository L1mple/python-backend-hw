import os, threading, time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DatabaseError

URL=os.getenv("DATABASE_URL","sqlite:///./app.db")
E=create_engine(URL, future=True)

def _prep():
    with E.begin() as c:
        c.execute(text("drop table if exists t_nr"))
        c.execute(text("create table t_nr(id int primary key, v int)"))
        c.execute(text("insert into t_nr(id,v) values (1,0) on conflict (id) do update set v=excluded.v" if URL.startswith("sqlite") else "insert into t_nr(id,v) values (1,0) on conflict (id) do nothing"))
        c.execute(text("drop table if exists t_ph"))
        c.execute(text("create table t_ph(id serial primary key, tag int)")) if not URL.startswith("sqlite") else c.execute(text("create table t_ph(id integer primary key autoincrement, tag int)"))
        c.execute(text("delete from t_ph"))
        c.execute(text("insert into t_ph(tag) values (1),(1),(2)"))
        c.execute(text("drop table if exists oncall"))
        c.execute(text("create table oncall(id int primary key, working bool)"))
        # should works
        c.execute(text("insert into oncall(id,working) values (1,true) on conflict (id) do update set working=excluded.working" if URL.startswith("sqlite") else "insert into oncall(id,working) values (1,true) on conflict (id) do nothing"))
        c.execute(text("insert into oncall(id,working) values (2,true) on conflict (id) do update set working=excluded.working" if URL.startswith("sqlite") else "insert into oncall(id,working) values (2,true) on conflict (id) do nothing"))

def _engine(level):
    if URL.startswith("sqlite"): return create_engine(URL, future=True)
    return create_engine(URL, future=True, isolation_level=level)

def dirty_read():
    _prep()
    if not URL.startswith("postgres"):
        print("skip: dirty read demo depends on vendor"); return
    A=_engine("READ UNCOMMITTED")
    B=_engine("READ UNCOMMITTED")
    with A.begin() as a:
        a.execute(text("update t_nr set v=10 where id=1"))
        with B.begin() as b:
            r=b.execute(text("select v from t_nr where id=1")).scalar()
            print("dirty_read_read=",r)
        a.rollback()
    with E.begin() as c:
        r=c.execute(text("select v from t_nr where id=1")).scalar()
        print("after_rollback=",r)

def non_repeatable_read_read_committed():
    _prep()
    A=_engine("READ COMMITTED")
    B=_engine("READ COMMITTED")
    with A.connect() as a:
        a.exec_driver_sql("begin")
        r1=a.execute(text("select v from t_nr where id=1")).scalar()
        def w():
            with B.begin() as b:
                b.execute(text("update t_nr set v=20 where id=1"))
        t=threading.Thread(target=w); t.start(); t.join()
        r2=a.execute(text("select v from t_nr where id=1")).scalar()
        a.exec_driver_sql("commit")
        print("rc_v1=",r1,"rc_v2=",r2)

def repeatable_read_blocks_nonrepeatable():
    if not URL.startswith("postgres"):
        print("skip: rr demo depends on postgres"); return
    _prep()
    A=_engine("REPEATABLE READ")
    B=_engine("READ COMMITTED")
    with A.connect() as a:
        a.exec_driver_sql("begin")
        r1=a.execute(text("select v from t_nr where id=1")).scalar()
        def w():
            time.sleep(0.2)
            with B.begin() as b:
                b.execute(text("update t_nr set v=30 where id=1"))
        t=threading.Thread(target=w); t.start(); t.join()
        r2=a.execute(text("select v from t_nr where id=1")).scalar()
        a.exec_driver_sql("commit")
        print("rr_v1=",r1,"rr_v2=",r2)

def phantom_read_read_committed():
    _prep()
    A=_engine("READ COMMITTED")
    B=_engine("READ COMMITTED")
    with A.connect() as a:
        a.exec_driver_sql("begin")
        r1=a.execute(text("select count(*) from t_ph where tag=1")).scalar()
        def w():
            with B.begin() as b:
                b.execute(text("insert into t_ph(tag) values (1)"))
        t=threading.Thread(target=w); t.start(); t.join()
        r2=a.execute(text("select count(*) from t_ph where tag=1")).scalar()
        a.exec_driver_sql("commit")
        print("rc_ph1=",r1,"rc_ph2=",r2)

def repeatable_read_blocks_phantoms():
    if not URL.startswith("postgres"):
        print("skip: rr phantom demo depends on postgres"); return
    _prep()
    A=_engine("REPEATABLE READ")
    B=_engine("READ COMMITTED")
    with A.connect() as a:
        a.exec_driver_sql("begin")
        r1=a.execute(text("select count(*) from t_ph where tag=1")).scalar()
        def w():
            time.sleep(0.2)
            with B.begin() as b:
                b.execute(text("insert into t_ph(tag) values (1)"))
        t=threading.Thread(target=w); t.start(); t.join()
        r2=a.execute(text("select count(*) from t_ph where tag=1")).scalar()
        a.exec_driver_sql("commit")
        print("rr_ph1=",r1,"rr_ph2=",r2)

def write_skew_rr_vs_serializable():
    if not URL.startswith("postgres"):
        print("skip: serializable demo depends on postgres"); return
    _prep()
    def txn(level, val):
        eng=_engine(level)
        with eng.connect() as c:
            c.exec_driver_sql("begin")
            n=c.execute(text("select count(*) from oncall where working=true")).scalar()
            if n>=2:
                c.exec_driver_sql("commit"); print(level,"skip"); return
            c.execute(text("update oncall set working=false where id=:i"),{"i":val})
            try:
                c.exec_driver_sql("commit"); print(level,"commit")
            except DatabaseError as e:
                print(level,"rollback")
    with E.begin() as c:
        c.execute(text("update oncall set working=true where id in (1,2)"))
    t1=threading.Thread(target=txn,args=("REPEATABLE READ",1))
    t2=threading.Thread(target=txn,args=("REPEATABLE READ",2))
    t1.start(); t2.start(); t1.join(); t2.join()
    with E.begin() as c:
        r=c.execute(text("select count(*) from oncall where working=true")).scalar()
        print("rr_after=",r)
    with E.begin() as c:
        c.execute(text("update oncall set working=true where id in (1,2)"))
    t1=threading.Thread(target=txn,args=("SERIALIZABLE",1))
    t2=threading.Thread(target=txn,args=("SERIALIZABLE",2))
    t1.start(); t2.start(); t1.join(); t2.join()
    with E.begin() as c:
        r=c.execute(text("select count(*) from oncall where working=true")).scalar()
        print("ser_after=",r)

if __name__=="__main__":
    dirty_read()
    non_repeatable_read_read_committed()
    repeatable_read_blocks_nonrepeatable()
    phantom_read_read_committed()
    repeatable_read_blocks_phantoms()
    write_skew_rr_vs_serializable()