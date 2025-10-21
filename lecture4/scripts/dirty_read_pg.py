from util import conn, begin, reset_items
import threading, time

reset_items()

def t1():
    c = conn(); cur = c.cursor()
    begin(cur, "READ COMMITTED")
    cur.execute("UPDATE items SET price = 999 WHERE name='A'")
    print("T1 updated A=999 not committed")
    time.sleep(3)
    cur.execute("ROLLBACK"); print("T1 rolled back")
    cur.close(); c.close()

def t2():
    c = conn(); cur = c.cursor()
    begin(cur, "READ UNCOMMITTED")  # в PG это RC
    time.sleep(1)
    cur.execute("SELECT price FROM items WHERE name='A'")
    print("T2 sees (no dirty read):", cur.fetchone()[0])
    cur.execute("COMMIT"); cur.close(); c.close()

if __name__ == "__main__":
    th1 = threading.Thread(target=t1); th2 = threading.Thread(target=t2)
    th1.start(); th2.start(); th1.join(); th2.join()
