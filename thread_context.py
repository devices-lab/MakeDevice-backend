"""
Thread-local (let each thread have a different, private copy of some variables)
"""
import threading

thread_context = threading.local()
