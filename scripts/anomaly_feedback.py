"""
Anomaly Feedback Collection Tool
Allows users to mark anomalies as true/false positives for model evaluation
"""

import requests
import json
from datetime import datetime

ES_HOST = "http://localhost:9200"
ML_INDEX = "firefox-ml-anomalies-*"

def get_recent_unverified_anomalies(count=10):
    """Fetch recent unverified anomalies"""
    query = {
        "size": count,
        "query": {
            "bool": {
                "must_not": [
                    {"exists": {"field": "is_verified"}}
                ]
            }
        },
        "sort": [{"@timestamp": "desc"}]
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    data = response.json()
    
    anomalies = []
    for hit in data['hits']['hits']:
        anomalies.append({
            'id': hit['_id'],
            'index': hit['_index'],
            'data': hit['_source']
        })
    
    return anomalies

def mark_anomaly(anomaly_id, index, is_true_positive):
    """Mark anomaly as true/false positive"""
    update_body = {
        "doc": {
            "is_verified": True,
            "is_true_positive": is_true_positive,
            "verified_at": datetime.now().isoformat()
        }
    }
    
    response = requests.post(
        f"{ES_HOST}/{index}/_update/{anomaly_id}",
        json=update_body,
        headers={"Content-Type": "application/json"}
    )
    
    return response.status_code == 200

def display_anomaly(anomaly, index):
    """Display anomaly details"""
    data = anomaly['data']
    
    print(f"\n{'═' * 60}")
    print(f"Anomaly #{index + 1}")
    print(f"{'═' * 60}")
    print(f"Timestamp:      {data['@timestamp']}")
    print(f"Type:           {data['anomaly_type']}")
    print(f"Score:          {data['anomaly_score']:.2f}")
    print(f"Severity:       {data['severity']}")
    print(f"Recommendation: {data['recommendation']}")
    print(f"\nFeatures:")
    for key, value in data['features'].items():
        print(f"  {key:25s}: {value}")
    print(f"{'─' * 60}")

def main():
    """Main feedback collection loop"""
    print("🤖 ML Anomaly Feedback Collection Tool")
    print("=" * 60)
    print("Help improve model precision by verifying anomalies\n")
    
    anomalies = get_recent_unverified_anomalies(count=20)
    
    if not anomalies:
        print("✅ No unverified anomalies found!")
        return
    
    print(f"Found {len(anomalies)} unverified anomalies\n")
    
    verified_count = 0
    tp_count = 0
    fp_count = 0
    
    for idx, anomaly in enumerate(anomalies):
        display_anomaly(anomaly, idx)
        
        while True:
            response = input("\nIs this a TRUE anomaly? (y/n/s=skip/q=quit): ").strip().lower()
            
            if response == 'q':
                print(f"\n✅ Verified {verified_count} anomalies")
                print(f"   True Positives: {tp_count}")
                print(f"   False Positives: {fp_count}")
                return
            elif response == 's':
                break
            elif response in ['y', 'n']:
                is_true = (response == 'y')
                
                if mark_anomaly(anomaly['id'], anomaly['index'], is_true):
                    verified_count += 1
                    if is_true:
                        tp_count += 1
                        print("✅ Marked as TRUE POSITIVE")
                    else:
                        fp_count += 1
                        print("⚠️  Marked as FALSE POSITIVE")
                else:
                    print("❌ Failed to update")
                break
            else:
                print("Invalid input. Use y/n/s/q")
    
    print(f"\n✅ Feedback collection complete!")
    print(f"   Verified: {verified_count}/{len(anomalies)}")
    print(f"   True Positives: {tp_count}")
    print(f"   False Positives: {fp_count}")
    print(f"   Precision: {tp_count/verified_count*100:.1f}%" if verified_count > 0 else "")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Feedback collection interrupted")
