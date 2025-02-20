import time
from datetime import datetime

class PageTiming:
    transition_history = []

    @staticmethod
    def log_transition(from_page, to_page, duration):
        """Log a page transition with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        PageTiming.transition_history.append({
            'timestamp': timestamp,
            'from': from_page,
            'to': to_page,
            'duration': duration
        })
        print(f"[{timestamp}] {from_page} → {to_page}: {duration:.3f}s")

    @staticmethod
    def start_timing():
        """Start timing a transition"""
        return time.time()

    @staticmethod
    def end_timing(start_time, from_page, to_page):
        """End timing and log the transition"""
        duration = time.time() - start_time
        PageTiming.log_transition(from_page, to_page, duration)
        return duration
