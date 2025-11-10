"""
ML Anomaly Viewer - Easy CLI tool to view anomaly detection results
"""

import requests
import json
from datetime import datetime
from tabulate import tabulate
from colorama import init, Fore, Style

init(autoreset=True)

ES_HOST = "http://localhost:9200"
ML_INDEX = "firefox-ml-anomalies-*"


def get_latest_anomalies(count=10):
    """Get latest detected anomalies"""
    query = {
        "size": count,
        "sort": [{"@timestamp": "desc"}]
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    data = response.json()
    
    anomalies = []
    for hit in data['hits']['hits']:
        src = hit['_source']
        anomalies.append([
            src['@timestamp'][:19],
            src['anomaly_type'],
            f"{src['anomaly_score']:.2f}",
            src['severity'],
            src['recommendation'][:60] + "..."
        ])
    
    print(f"\n{Fore.CYAN}📊 Latest {count} Anomalies{Style.RESET_ALL}")
    print(tabulate(anomalies, headers=['Timestamp', 'Type', 'Score', 'Severity', 'Recommendation'], tablefmt='grid'))


def get_anomaly_summary():
    """Get summary statistics"""
    count_response = requests.get(f"{ES_HOST}/{ML_INDEX}/_count")
    total = count_response.json()['count']
    
    query = {
        "size": 0,
        "aggs": {
            "by_type": {"terms": {"field": "anomaly_type.keyword"}},
            "by_severity": {"terms": {"field": "severity.keyword"}},
            "avg_score": {"avg": {"field": "anomaly_score"}}
        }
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    data = response.json()
    
    print(f"\n{Fore.GREEN}📈 ML Anomaly Detection Summary{Style.RESET_ALL}")
    print(f"{'='*50}")
    print(f"{Fore.YELLOW}Total Anomalies: {total}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Average Score: {data['aggregations']['avg_score']['value']:.2f}{Style.RESET_ALL}\n")
    
    print(f"{Fore.CYAN}By Type:{Style.RESET_ALL}")
    types = [[b['key'], b['doc_count']] for b in data['aggregations']['by_type']['buckets']]
    print(tabulate(types, headers=['Type', 'Count'], tablefmt='simple'))
    
    print(f"\n{Fore.CYAN}By Severity:{Style.RESET_ALL}")
    severities = [[b['key'], b['doc_count']] for b in data['aggregations']['by_severity']['buckets']]
    print(tabulate(severities, headers=['Severity', 'Count'], tablefmt='simple'))


def get_critical_anomalies():
    """Get only critical severity anomalies"""
    query = {
        "size": 20,
        "sort": [{"anomaly_score": "desc"}],
        "query": {
            "term": {"severity.keyword": "critical"}
        }
    }
    
    response = requests.post(f"{ES_HOST}/{ML_INDEX}/_search", json=query)
    data = response.json()
    
    anomalies = []
    for hit in data['hits']['hits']:
        src = hit['_source']
        anomalies.append([
            src['@timestamp'][:19],
            src['anomaly_type'],
            f"{src['anomaly_score']:.2f}",
            src['recommendation'][:80]
        ])
    
    print(f"\n{Fore.RED}🚨 Critical Anomalies{Style.RESET_ALL}")
    print(tabulate(anomalies, headers=['Timestamp', 'Type', 'Score', 'Recommendation'], tablefmt='grid'))


def show_menu():
    """Display menu options"""
    print(f"\n{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}🤖 ML Anomaly Detection - Quick Viewer{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
    print("1. Latest Anomalies (Last 10)")
    print("2. Anomaly Summary & Statistics")
    print("3. Critical Anomalies Only")
    print("4. Open Kibana Dashboard")
    print("Q. Quit")
    print()


def main():
    """Main menu loop"""
    while True:
        show_menu()
        choice = input("Select option: ").strip().upper()
        
        if choice == '1':
            get_latest_anomalies()
        elif choice == '2':
            get_anomaly_summary()
        elif choice == '3':
            get_critical_anomalies()
        elif choice == '4':
            import webbrowser
            webbrowser.open('http://localhost:5601/app/dashboards')
        elif choice == 'Q':
            print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid option{Style.RESET_ALL}")
        
        input("\nPress Enter to continue...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
