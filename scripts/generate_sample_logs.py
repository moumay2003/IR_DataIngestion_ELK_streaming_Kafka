"""
Generate sample Firefox build logs for testing
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Sample log patterns
LOG_PATTERNS = [
    "0:05.12 {test_name} TEST-START | {test_class}.{test_method}",
    "0:05.15 {test_name} TEST-PASS | {test_class}.{test_method} | duration {duration}ms",
    "0:05.20 {test_name} TEST-UNEXPECTED-FAIL | {test_class}.{test_method} | {error}",
    "0:05.25 WARNING: {warning_msg}",
    "0:05.30 ERROR: {error_msg}",
    "0:05.35 {test_name} Assertion failure: {assertion}",
    "0:05.40 INFO: Finished test suite in {total_time}ms",
]

TEST_CLASSES = [
    "TestClick", "TestRendering", "TestPerformance", "TestNavigation", 
    "TestMemory", "TestNetwork", "TestUI", "TestSecurity"
]

TEST_METHODS = [
    "test_element_click", "test_button_render", "test_page_load", 
    "test_scroll_performance", "test_memory_leak", "test_network_latency",
    "test_ui_responsiveness", "test_security_headers"
]

ERRORS = [
    "Element not found", "Timeout waiting for element", "Assertion failed",
    "Memory limit exceeded", "Network connection failed", "Invalid state"
]

WARNINGS = [
    "Deprecated API usage", "Resource leak detected", "Performance degradation",
    "Cache miss ratio high", "Thread pool exhausted"
]

def generate_log_file(output_dir, file_number, lines_per_file=1000):
    """Generate a single log file"""
    filename = f"build_log_{file_number:03d}.txt"
    filepath = Path(output_dir) / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for i in range(lines_per_file):
            # Choose random log pattern
            pattern = random.choice(LOG_PATTERNS)
            
            # Fill in template
            log_line = pattern.format(
                test_name=f"test_{random.choice(TEST_CLASSES).lower()}.py",
                test_class=random.choice(TEST_CLASSES),
                test_method=random.choice(TEST_METHODS),
                duration=random.randint(100, 5000),
                error=random.choice(ERRORS),
                warning_msg=random.choice(WARNINGS),
                error_msg=random.choice(ERRORS),
                assertion=f"Expected {random.randint(1,100)}, got {random.randint(1,100)}",
                total_time=random.randint(5000, 30000)
            )
            
            f.write(log_line + '\n')
    
    return filepath

def main():
    """Generate sample log files"""
    output_dir = Path("../data/firefox-build-logs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    num_files = 10
    lines_per_file = 1000
    
    print(f"Generating {num_files} log files with {lines_per_file} lines each...")
    
    for i in range(1, num_files + 1):
        filepath = generate_log_file(output_dir, i, lines_per_file)
        print(f"Created: {filepath}")
    
    print(f"\nGenerated {num_files} files in {output_dir}")
    print(f"Total lines: {num_files * lines_per_file:,}")
    print(f"\nRun producer with:")
    print(f'  python kafka_producer_minimal.py --log-dir "{output_dir}"')

if __name__ == '__main__':
    main()
