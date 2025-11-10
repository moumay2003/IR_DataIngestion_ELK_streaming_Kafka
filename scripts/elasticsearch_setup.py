"""
Elasticsearch Setup Script
Creates index templates and prepares Elasticsearch for Firefox log ingestion
"""

import json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElasticsearchSetup:
    """Setup Elasticsearch indices and mappings"""
    
    def __init__(self, es_host='localhost:9200'):
        """Initialize Elasticsearch connection"""
        self.es = Elasticsearch([f'http://{es_host}'])
        logger.info(f"Connected to Elasticsearch at {es_host}")
    
    def create_index_template(self):
        """Create index template for Firefox logs"""
        
        template = {
            "index_patterns": ["firefox-logs-*", "firefox-anomalies-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.refresh_interval": "5s",
                    "index.max_result_window": 50000
                },
                "mappings": {
                    "properties": {
                        "@timestamp": {
                            "type": "date"
                        },
                        "log_time": {
                            "type": "keyword"
                        },
                        "log_level": {
                            "type": "keyword"
                        },
                        "log_message": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "raw_message": {
                            "type": "text"
                        },
                        "build_id": {
                            "type": "keyword"
                        },
                        "builder": {
                            "type": "keyword"
                        },
                        "slave": {
                            "type": "keyword"
                        },
                        "buildid": {
                            "type": "keyword"
                        },
                        "revision": {
                            "type": "keyword"
                        },
                        "git_revision": {
                            "type": "keyword"
                        },
                        "branch": {
                            "type": "keyword"
                        },
                        "result": {
                            "type": "keyword"
                        },
                        "filename": {
                            "type": "keyword"
                        },
                        "file_timestamp": {
                            "type": "date"
                        },
                        "file_event_time": {
                            "type": "date"
                        },
                        "line_number": {
                            "type": "integer"
                        },
                        "process_id": {
                            "type": "keyword"
                        },
                        "message_type": {
                            "type": "keyword"
                        },
                        "event_type": {
                            "type": "keyword"
                        },
                        "test_name": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 512
                                }
                            }
                        },
                        "test_status": {
                            "type": "keyword"
                        },
                        "test_duration": {
                            "type": "integer"
                        },
                        "duration_ms": {
                            "type": "integer"
                        },
                        "elapsed_time": {
                            "type": "float"
                        },
                        "suite_duration": {
                            "type": "integer"
                        },
                        "total_tests": {
                            "type": "integer"
                        },
                        "warning_message": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 512
                                }
                            }
                        },
                        "warning_severity": {
                            "type": "keyword"
                        },
                        "file_path": {
                            "type": "text",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 512
                                }
                            }
                        },
                        "error_code": {
                            "type": "keyword"
                        },
                        "fail_reason": {
                            "type": "text"
                        },
                        "severity": {
                            "type": "keyword"
                        },
                        "anomaly_type": {
                            "type": "keyword"
                        },
                        "is_anomaly": {
                            "type": "boolean"
                        },
                        "potential_anomaly": {
                            "type": "boolean"
                        },
                        "tags": {
                            "type": "keyword"
                        },
                        "kafka_topic": {
                            "type": "keyword"
                        },
                        "kafka_partition": {
                            "type": "integer"
                        },
                        "kafka_offset": {
                            "type": "long"
                        },
                        "parsed": {
                            "type": "keyword"
                        }
                    }
                }
            }
        }
        
        # Create index template
        response = self.es.indices.put_index_template(
            name='firefox-logs-template',
            body=template
        )
        
        logger.info("Index template created successfully")
        return response
    
    def create_anomaly_detection_job(self):
        """
        Create ML anomaly detection job configuration
        Note: This requires X-Pack ML (paid feature) or basic license
        """
        
        job_config = {
            "description": "Detect anomalies in Firefox build/test logs",
            "analysis_config": {
                "bucket_span": "15m",
                "detectors": [
                    {
                        "detector_description": "High error rate",
                        "function": "count",
                        "by_field_name": "log_level"
                    },
                    {
                        "detector_description": "Unusual test failures",
                        "function": "count",
                        "by_field_name": "test_status",
                        "partition_field_name": "builder"
                    },
                    {
                        "detector_description": "Abnormal test duration",
                        "function": "high_mean",
                        "field_name": "test_duration",
                        "by_field_name": "test_name.keyword"
                    },
                    {
                        "detector_description": "Warning spikes",
                        "function": "count",
                        "by_field_name": "warning_severity"
                    }
                ],
                "influencers": [
                    "builder",
                    "slave",
                    "test_name.keyword",
                    "log_level"
                ]
            },
            "data_description": {
                "time_field": "@timestamp"
            }
        }
        
        logger.info("Anomaly detection job configuration prepared")
        return job_config
    
    def create_visualizations_config(self):
        """Generate Kibana visualization configuration"""
        
        visualizations = {
            "dashboards": [
                {
                    "name": "Firefox Build Overview",
                    "description": "Overall build and test metrics",
                    "visualizations": [
                        "Total Tests Run",
                        "Test Status Distribution",
                        "Build Success Rate",
                        "Average Test Duration"
                    ]
                },
                {
                    "name": "Anomaly Detection Dashboard",
                    "description": "Detected anomalies and warnings",
                    "visualizations": [
                        "Anomaly Timeline",
                        "Warning Severity Heatmap",
                        "Error Code Frequency",
                        "Failed Tests Table"
                    ]
                }
            ],
            "searches": [
                {
                    "name": "All Anomalies",
                    "query": "is_anomaly:true"
                },
                {
                    "name": "Test Failures",
                    "query": "test_status:failed OR tags:test_failure"
                },
                {
                    "name": "Critical Warnings",
                    "query": "warning_severity:high OR tags:critical_warning"
                },
                {
                    "name": "Slow Tests",
                    "query": "tags:slow_test AND test_duration:>60000"
                }
            ]
        }
        
        return visualizations
    
    def setup_all(self):
        """Run all setup tasks"""
        logger.info("Starting Elasticsearch setup...")
        
        # Wait for Elasticsearch to be ready
        if not self.es.ping():
            logger.error("Elasticsearch is not responding")
            return False
        
        logger.info("Elasticsearch is ready")
        
        # Create index template
        self.create_index_template()
        
        # Generate configurations
        anomaly_config = self.create_anomaly_detection_job()
        vis_config = self.create_visualizations_config()
        
        # Save configurations to files
        with open('anomaly_detection_config.json', 'w') as f:
            json.dump(anomaly_config, f, indent=2)
        logger.info("Saved anomaly detection config to anomaly_detection_config.json")
        
        with open('kibana_visualizations_config.json', 'w') as f:
            json.dump(vis_config, f, indent=2)
        logger.info("Saved Kibana config to kibana_visualizations_config.json")
        
        logger.info("Setup completed successfully!")
        return True


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Elasticsearch for Firefox logs')
    parser.add_argument(
        '--es-host',
        type=str,
        default='localhost:9200',
        help='Elasticsearch host:port'
    )
    
    args = parser.parse_args()
    
    setup = ElasticsearchSetup(es_host=args.es_host)
    setup.setup_all()


if __name__ == '__main__':
    main()
