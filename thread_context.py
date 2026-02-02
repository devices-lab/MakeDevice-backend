"""
Thread-local (let each thread have a different, private copy of some variables)

Always do "import thread_context". NEVER do "from thread_context import thread_context"
as it will refer to a different namespace with different variables
"""
import threading

thread_context = threading.local()

# NOTE: NOT USE global variables in ANY code, since those are shared between all threads!
job_id = None
job_folder = None
frame_index = 0
error_message = ""
