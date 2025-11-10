"""
Anomaly Analysis Script
Performs advanced anomaly analysis on Firefox logs stored in Elasticsearch
"""

from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import json
import pandas as pd
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyAnalyzer:
    """Analyze anomalies in Firefox build logs"""
    
    def __init__(self, es_host='localhost:9200'):
        """Initialize connection to Elasticsearch"""
        self.es = Elasticsearch([f'http://{es_host}'])
        logger.info(f"Connected to Elasticsearch at {es_host}")
    
    def get_anomaly_summary(self, days_back=7):
        """Get summary of anomalies over specified days"""
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"is_anomaly": True}},
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{days_back}d/d"
                                }
                            }
                        }
                    ]
                }
            },
            "aggs": {
                "anomaly_types": {
                    "terms": {
                        "field": "tags",
                        "size": 20
                    }
                },
                "by_builder": {
                    "terms": {
                        "field": "builder.keyword",
                        "size": 10
                    }
                },
                "timeline": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "calendar_interval": "1h"
                    }
                }
            },
            "size": 0
        }
        
        result = self.es.search(index="firefox-logs-*", body=query)
        
        return {
            "total_anomalies": result['hits']['total']['value'],
            "anomaly_types": result['aggregations']['anomaly_types']['buckets'],
            "by_builder": result['aggregations']['by_builder']['buckets'],
            "timeline": result['aggregations']['timeline']['buckets']
        }
    
    def get_top_failing_tests(self, limit=20):
        """Get most frequently failing tests"""
        
        query = {
            "query": {
                "term": {"test_status": "failed"}
            },
            "aggs": {
                "failing_tests": {
                    "terms": {
                        "field": "test_name.keyword",
                        "size": limit,
                        "order": {"_count": "desc"}
                    }
                }
            },
            "size": 0
        }
        
        result = self.es.search(index="firefox-logs-*", body=query)
        return result['aggregations']['failing_tests']['buckets']
    
    def get_error_code_distribution(self):
        """Get distribution of error codes"""
        
        query = {
            "query": {
                "exists": {"field": "error_code"}
            },
            "aggs": {
                "error_codes": {
                    "terms": {
                        "field": "error_code",
                        "size": 50
                    }
                }
            },
            "size": 0
        }
        
        result = self.es.search(index="firefox-logs-*", body=query)
        return result['aggregations']['error_codes']['buckets']
    
    def get_performance_stats(self):
        """Get test performance statistics"""
        
        query = {
            "query": {
                "exists": {"field": "test_duration"}
            },
            "aggs": {
                "duration_stats": {
                    "stats": {
                        "field": "test_duration"
                    }
                },
                "slow_tests": {
                    "filter": {
                        "range": {"test_duration": {"gte": 60000}}
                    },
                    "aggs": {
                        "slowest": {
                            "terms": {
                                "field": "test_name.keyword",
                                "size": 10,
                                "order": {"avg_duration": "desc"}
                            },
                            "aggs": {
                                "avg_duration": {
                                    "avg": {"field": "test_duration"}
                                }
                            }
                        }
                    }
                }
            },
            "size": 0
        }
        
        result = self.es.search(index="firefox-logs-*", body=query)
        return {
            "stats": result['aggregations']['duration_stats'],
            "slow_tests": result['aggregations']['slow_tests']['slowest']['buckets']
        }
    
    def get_warning_severity_trends(self):
        """Get warning severity trends over time"""
        
        query = {
            "query": {
                "exists": {"field": "warning_severity"}
            },
            "aggs": {
                "severity_timeline": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "calendar_interval": "1h"
                    },
                    "aggs": {
                        "by_severity": {
                            "terms": {
                                "field": "warning_severity"
                            }
                        }
                    }
                }
            },
            "size": 0
        }
        
        result = self.es.search(index="firefox-logs-*", body=query)
        return result['aggregations']['severity_timeline']['buckets']
    
    def detect_anomaly_patterns(self):
        """Detect unusual patterns in log data"""
        
        patterns = {}
        
        # 1. Sudden spike in errors
        query = {
            "query": {"term": {"log_level": "ERROR"}},
            "aggs": {
                "errors_over_time": {
                    "date_histogram": {
                        "field": "@timestamp",
                        "calendar_interval": "15m"
                    }
                }
            },
            "size": 0
        }
        
        result = self.es.search(index="firefox-logs-*", body=query)
        buckets = result['aggregations']['errors_over_time']['buckets']
        
        if buckets:
            counts = [b['doc_count'] for b in buckets]
            avg = sum(counts) / len(counts)
            max_count = max(counts)
            
            if max_count > avg * 3:  # 3x spike
                patterns['error_spike'] = {
                    "detected": True,
                    "avg": avg,
                    "max": max_count,
                    "threshold_multiplier": max_count / avg if avg > 0 else 0
                }
        
        # 2. New error types
        query = {
            "query": {
                "range": {
                    "@timestamp": {"gte": "now-1h"}
                }
            },
            "aggs": {
                "recent_errors": {
                    "terms": {
                        "field": "error_code",
                        "size": 50
                    }
                }
            },
            "size": 0
        }
        
        recent = self.es.search(index="firefox-logs-*", body=query)
        
        query["query"]["range"]["@timestamp"] = {"gte": "now-7d", "lt": "now-1h"}
        historical = self.es.search(index="firefox-logs-*", body=query)
        
        recent_errors = {b['key'] for b in recent['aggregations']['recent_errors']['buckets']}
        historical_errors = {b['key'] for b in historical['aggregations']['recent_errors']['buckets']}
        
        new_errors = recent_errors - historical_errors
        if new_errors:
            patterns['new_error_codes'] = list(new_errors)
        
        return patterns
    
    def generate_report(self):
        """Generate comprehensive anomaly report"""
        
        logger.info("Generating anomaly report...")
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self.get_anomaly_summary(),
            "top_failing_tests": self.get_top_failing_tests(),
            "error_codes": self.get_error_code_distribution(),
            "performance": self.get_performance_stats(),
            "warning_trends": self.get_warning_severity_trends(),
            "detected_patterns": self.detect_anomaly_patterns()
        }
        
        # Save to file
        filename = f"anomaly_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {filename}")
        
        # Print summary
        print("\n" + "="*60)
        print("ANOMALY DETECTION REPORT")
        print("="*60)
        print(f"\nTotal Anomalies: {report['summary']['total_anomalies']}")
        
        print("\nTop 5 Anomaly Types:")
        for item in report['summary']['anomaly_types'][:5]:
            print(f"  - {item['key']}: {item['doc_count']}")
        
        print("\nTop 5 Failing Tests:")
        for item in report['top_failing_tests'][:5]:
            print(f"  - {item['key']}: {item['doc_count']} failures")
        
        print("\nPerformance Stats:")
        stats = report['performance']['stats']
        print(f"  - Avg Test Duration: {stats['avg']:.2f}ms")
        print(f"  - Max Test Duration: {stats['max']:.2f}ms")
        print(f"  - Min Test Duration: {stats['min']:.2f}ms")
        
        if report['detected_patterns'].get('error_spike'):
            spike = report['detected_patterns']['error_spike']
            print(f"\n⚠️  ERROR SPIKE DETECTED!")
            print(f"  - Average errors: {spike['avg']:.1f}")
            print(f"  - Peak errors: {spike['max']}")
            print(f"  - Spike factor: {spike['threshold_multiplier']:.1f}x")
        
        if report['detected_patterns'].get('new_error_codes'):
            print(f"\n⚠️  NEW ERROR CODES DETECTED:")
            for code in report['detected_patterns']['new_error_codes']:
                print(f"  - {code}")
        
        print("\n" + "="*60)
        
        return report


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze anomalies in Firefox logs')
    parser.add_argument(
        '--es-host',
        type=str,
        default='localhost:9200',
        help='Elasticsearch host:port'
    )
    
    args = parser.parse_args()
    
    analyzer = AnomalyAnalyzer(es_host=args.es_host)
    analyzer.generate_report()


if __name__ == '__main__':
    main()
