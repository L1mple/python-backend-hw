from util import conn, begin, reset_items
import threading, time

def show(cur, tag):
    cur.execute("SHOW TRANSACTION ISOLATION LEVEL")
    print(f"{tag} iso:", cur.fetchone()[0])

reset_items()

def t1_rc():
    c = conn(); cur = c.cursor()
    begin(cur, "READ COMMITTED"); show(cur, "T1 RC")
    cur.execute("SELECT price FROM items WHERE name='B'"); r1 = cur.fetchone()[0]
    print("T1 first B:", r1)
    time.sleep(3)
    cur.execute("SELECT price FROM items WHERE name='B'"); r2 = cur.fetchone()[0]
    print("T1 second B (changed):", r2)
    cur.execute("COMMIT"); cur.close(); c.close()

def t2_upd():
    c = conn(); cur = c.cursor()
    time.sleep(1)
    begin(cur, "READ COMMITTED"); show(cur, "T2 RC")
    cur.execute("UPDATE items SET price = price + 1 WHERE name='B'")
    cur.execute("COMMIT"); print("T2 committed update B")
    cur.close(); c.close()

th1 = threading.Thread(target=t1_rc); th2 = threading.Thread(target=t2_upd)
th1.start(); th2.start(); th1.join(); th2.join()

reset_items()

def t1_rr():
    c = conn(); cur = c.cursor()
    begin(cur, "REPEATABLE READ"); show(cur, "T1 RR")
    cur.execute("SELECT price FROM items WHERE name='B'"); r1 = cur.fetchone()[0]
    print("T1 RR first:", r1)
    time.sleep(3)
    cur.execute("SELECT price FROM items WHERE name='B'"); r2 = cur.fetchone()[0]
    print("T1 RR second (same):", r2)
    cur.execute("COMMIT"); cur.close(); c.close()

def t2_rr():
    c = conn(); cur = c.cursor()
    time.sleep(1)
    begin(cur, "READ COMMITTED"); show(cur, "T2 RC")
    cur.execute("UPDATE items SET price = price + 1 WHERE name='B'")
    cur.execute("COMMIT"); print("T2 updated B under RC")
    cur.close(); c.close()

th1 = threading.Thread(target=t1_rr); th2 = threading.Thread(target=t2_rr)
th1.start(); th2.start(); th1.join(); th2.join()
