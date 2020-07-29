python3 tls_flows.py 3.pcapng > flow2.csv
python3 tls_flows.py 3.pcapng > flow3.csv
python3 tls_flows.py 4.pcapng > flow4.csv
python3 tls_flows.py 5.pcapng > flow5.csv
python3 tls_flows.py 6.pcapng > flow6.csv
cat flow*.csv > flow.csv