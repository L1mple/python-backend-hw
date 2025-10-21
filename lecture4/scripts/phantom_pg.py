from util import conn, begin, reset_items
import threading, time
import psycopg

def show(cur, tag):
    cur.execute("SHOW TRANSACTION ISOLATION LEVEL")
    print(f"{tag} iso:", cur.fetchone()[0])

reset_items()

def t1_rc():
    c = conn(); cur = c.cursor()
    begin(cur, "READ COMMITTED"); show(cur, "T1 RC")
    cur.execute("SELECT COUNT(*) FROM items WHERE price >= 150 AND deleted = FALSE")
    n1 = cur.fetchone()[0]; print("T1 RC count1:", n1)
    time.sleep(3)
    cur.execute("SELECT COUNT(*) FROM items WHERE price >= 150 AND deleted = FALSE")
    n2 = cur.fetchone()[0]; print("T1 RC count2 (phantom expected):", n2)
    cur.execute("COMMIT"); cur.close(); c.close()

def t2_ins():
    c = conn(); cur = c.cursor()
    time.sleep(1)
    begin(cur, "READ COMMITTED"); show(cur, "T2 RC")
    cur.execute("INSERT INTO items(name,price,deleted) VALUES ('PH', 1000, FALSE)")
    cur.execute("COMMIT"); print("T2 inserted PH=1000")
    cur.close(); c.close()

th1 = threading.Thread(target=t1_rc); th2 = threading.Thread(target=t2_ins)
th1.start(); th2.start(); th1.join(); th2.join()

reset_items()

def t1_ser():
    c = conn(); cur = c.cursor()
    try:
        begin(cur, "SERIALIZABLE"); show(cur, "T1 SER")
        cur.execute("SELECT COUNT(*) FROM items WHERE price >= 150 AND deleted = FALSE")
        n1 = cur.fetchone()[0]; print("T1 SER count1:", n1)
        time.sleep(3)
        cur.execute("SELECT COUNT(*) FROM items WHERE price >= 150 AND deleted = FALSE")
        n2 = cur.fetchone()[0]; print("T1 SER count2 (same):", n2)
        cur.execute("COMMIT"); print("T1 SER committed")
    except psycopg.errors.SerializationFailure as e:
        print("T1 SER serialization failure:", e.__class__.__name__); cur.execute("ROLLBACK")
    finally:
        cur.close(); c.close()

def t2_ser():
    c = conn(); cur = c.cursor()
    try:
        time.sleep(1)
        begin(cur, "SERIALIZABLE"); show(cur, "T2 SER")
        cur.execute("INSERT INTO items(name,price,deleted) VALUES ('PH2', 500, FALSE)")
        cur.execute("COMMIT"); print("T2 SER committed")
    except psycopg.errors.SerializationFailure as e:
        print("T2 SER serialization failure:", e.__class__.__name__)
        try: cur.execute("ROLLBACK")
        except: pass
    finally:
        cur.close(); c.close()

th1 = threading.Thread(target=t1_ser); th2 = threading.Thread(target=t2_ser)
th1.start(); th2.start(); th1.join(); th2.join()
