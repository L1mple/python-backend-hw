from lost_update import run_all as run_lost_update
from non_repeatable_read import run_all as run_non_repeatable_read
from phantom_reader import run_all as run_phantom_reader
from write_skew import run_all as run_write_skew
from dirty_read import run_all as run_dirty_reads

if __name__ == "__main__":
    run_dirty_reads()
    run_lost_update()
    run_non_repeatable_read()
    run_phantom_reader()
    run_write_skew()
