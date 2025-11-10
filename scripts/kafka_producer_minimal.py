"""
Minimal Kafka Producer - Sends Raw Log Lines
All parsing is done in Logstash
"""

import os
import time
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MinimalFirefoxLogProducer:
    """Minimal producer - sends raw log lines to Kafka"""
    
    def __init__(self, bootstrap_servers='localhost:9092', topic='firefox-build-logs'):
        """Initialize Kafka producer"""
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: v.encode('utf-8'),  # Just encode string
            compression_type='gzip',
            acks='all',
            retries=3
        )
        logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
    
    def process_log_file(self, file_path):
        """Send raw log lines to Kafka with minimal metadata in headers"""
        logger.info(f"Processing file: {file_path}")
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = 0
                for line_number, line in enumerate(f, 1):
                    if line.strip():  # Skip empty lines
                        # Send raw line with metadata in Kafka headers
                        self.producer.send(
                            self.topic,
                            value=line.strip(),  # Raw log line
                            headers=[
                                ('filename', filename.encode('utf-8')),
                                ('line_number', str(line_number).encode('utf-8')),
                                ('filepath', file_path.encode('utf-8'))
                            ]
                        )
                        line_count += 1
                        
                        if line_count % 1000 == 0:
                            logger.info(f"Processed {line_count} lines from {filename}")
                
                logger.info(f"Completed {filename}: {line_count} lines sent to Kafka")
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def process_directory(self, directory_path, pattern='*.txt', recursive=True):
        """Process all log files in a directory"""
        logger.info(f"Scanning directory: {directory_path}")
        path = Path(directory_path)
        
        log_files = list(path.rglob(pattern)) if recursive else list(path.glob(pattern))
        logger.info(f"Found {len(log_files)} log files")
        
        for idx, log_file in enumerate(log_files, 1):
            logger.info(f"[{idx}/{len(log_files)}] Processing: {log_file.name}")
            self.process_log_file(str(log_file))
            time.sleep(0.1)
        
        logger.info("All files processed successfully")
    
    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stream Firefox logs to Kafka (minimal)')
    parser.add_argument('--log-dir', type=str, default='./data', help='Directory containing log files')
    parser.add_argument('--kafka-broker', type=str, default='localhost:9092', help='Kafka broker address')
    parser.add_argument('--topic', type=str, default='firefox-build-logs', help='Kafka topic name')
    parser.add_argument('--pattern', type=str, default='*.txt', help='File pattern to match')
    parser.add_argument('--no-recursive', action='store_true', help='Do not search subdirectories')
    
    args = parser.parse_args()
    
    producer = MinimalFirefoxLogProducer(
        bootstrap_servers=args.kafka_broker,
        topic=args.topic
    )
    
    try:
        producer.process_directory(
            directory_path=args.log_dir,
            pattern=args.pattern,
            recursive=not args.no_recursive
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        producer.close()


if __name__ == '__main__':
    main()
