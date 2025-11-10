"""
Unsupervised ML Model Evaluation
Evaluates model without requiring manual feedback/labels
"""

import requests
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

ES_HOST = "http://localhost:9200"
ML_INDEX = "firefox-ml-anomalies-*"

def fetch_anomalies(hours=24):
    """Fetch recent anomalies"""
    query = {
        "size": 1000,
        "query": {
            "range": {"@timestamp": {"gte": f"now-{hours}h"}}
        }
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    data = response.json()
    
    return [hit['_source'] for hit in data['hits']['hits']]

def evaluate_score_consistency():
    """Check if scores are consistent and meaningful"""
    anomalies = fetch_anomalies(24)
    
    if not anomalies:
        print("❌ No anomalies found")
        return
    
    scores = [a['anomaly_score'] for a in anomalies]
    
    print("\n📊 SCORE DISTRIBUTION ANALYSIS")
    print("=" * 60)
    print(f"Total Anomalies: {len(scores)}")
    print(f"Mean Score: {np.mean(scores):.2f}")
    print(f"Median Score: {np.median(scores):.2f}")
    print(f"Std Deviation: {np.std(scores):.2f}")
    print(f"Min Score: {np.min(scores):.2f}")
    print(f"Max Score: {np.max(scores):.2f}")
    print(f"95th Percentile: {np.percentile(scores, 95):.2f}")
    
    # Quality assessment
    mean_score = np.mean(scores)
    std_score = np.std(scores)
    
    print("\n🎯 QUALITY ASSESSMENT")
    if mean_score > 65 and std_score < 20:
        print("✅ GOOD - Consistent high-confidence detections")
    elif std_score > 30:
        print("⚠️ WARNING - High variance, model may need tuning")
    elif mean_score < 55:
        print("⚠️ WARNING - Low average scores, weak detections")
    else:
        print("✓ FAIR - Acceptable performance")
    
    # Plot distribution
    plt.figure(figsize=(10, 6))
    plt.hist(scores, bins=20, edgecolor='black', alpha=0.7)
    plt.axvline(mean_score, color='r', linestyle='--', label=f'Mean: {mean_score:.2f}')
    plt.axvline(np.median(scores), color='g', linestyle='--', label=f'Median: {np.median(scores):.2f}')
    plt.xlabel('Anomaly Score')
    plt.ylabel('Frequency')
    plt.title('Anomaly Score Distribution (Unsupervised Evaluation)')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig('unsupervised_score_distribution.png', dpi=300, bbox_inches='tight')
    print("\n✅ Saved: unsupervised_score_distribution.png")
    plt.show()

def evaluate_detection_stability():
    """Check if detection rate is stable over time"""
    query = {
        "size": 0,
        "query": {
            "range": {"@timestamp": {"gte": "now-24h"}}
        },
        "aggs": {
            "by_hour": {
                "date_histogram": {
                    "field": "@timestamp",
                    "fixed_interval": "1h"
                }
            }
        }
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    buckets = response.json()['aggregations']['by_hour']['buckets']
    
    hourly_counts = [b['doc_count'] for b in buckets]
    
    print("\n📈 TEMPORAL STABILITY ANALYSIS")
    print("=" * 60)
    print(f"Hours Analyzed: {len(hourly_counts)}")
    print(f"Avg Anomalies/Hour: {np.mean(hourly_counts):.2f}")
    print(f"Std Deviation: {np.std(hourly_counts):.2f}")
    
    consistency = 1 - (np.std(hourly_counts) / np.mean(hourly_counts)) if np.mean(hourly_counts) > 0 else 0
    print(f"Consistency Score: {consistency:.2%}")
    
    if consistency > 0.7:
        print("✅ STABLE - Consistent detection rate")
    elif consistency > 0.4:
        print("✓ MODERATE - Some variation expected")
    else:
        print("⚠️ UNSTABLE - High variation, investigate")

def evaluate_anomaly_diversity():
    """Check if model detects diverse types of anomalies"""
    anomalies = fetch_anomalies(24)
    
    types = [a['anomaly_type'] for a in anomalies]
    type_counts = pd.Series(types).value_counts()
    
    print("\n🔍 ANOMALY TYPE DIVERSITY")
    print("=" * 60)
    print(type_counts)
    
    # Calculate diversity (entropy)
    proportions = type_counts / type_counts.sum()
    entropy = -sum(p * np.log2(p) for p in proportions if p > 0)
    max_entropy = np.log2(len(type_counts))
    diversity_score = entropy / max_entropy if max_entropy > 0 else 0
    
    print(f"\nDiversity Score: {diversity_score:.2%}")
    
    if diversity_score > 0.7:
        print("✅ HIGH DIVERSITY - Model detects various anomaly types")
    elif diversity_score > 0.4:
        print("✓ MODERATE DIVERSITY")
    else:
        print("⚠️ LOW DIVERSITY - Model may be biased to one type")

def generate_unsupervised_report():
    """Generate complete unsupervised evaluation report"""
    print("\n" + "=" * 60)
    print("🤖 ML MODEL - UNSUPERVISED EVALUATION REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"No manual feedback required! ✅")
    
    evaluate_score_consistency()
    evaluate_detection_stability()
    evaluate_anomaly_diversity()
    
    print("\n" + "=" * 60)
    print("✅ Evaluation Complete!")
    print("\n💡 TIP: For more accurate metrics, add manual feedback:")
    print("   python anomaly_feedback.py")

if __name__ == '__main__':
    generate_unsupervised_report()
