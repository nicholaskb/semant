import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.graph_initializer import GraphInitializer

async def generate_ceo_report():
    # Initialize graph manager and load data
    graph_manager = KnowledgeGraphManager()
    initializer = GraphInitializer(graph_manager)
    
    # Load ontology and sample data
    await initializer.initialize_graph(
        'kg/schemas/core.ttl',
        'kg/schemas/sample_data.ttl'
    )
    
    # Collect key metrics
    report = []
    report.append("# Knowledge Graph Status Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Overall System Health
    report.append("## 1. System Health Overview")
    results = await graph_manager.query_graph("""
        SELECT ?machine ?status WHERE {
            ?machine rdf:type <http://example.org/core#Machine> ;
                    <http://example.org/core#hasStatus> ?status .
        }
    """)
    for r in results:
        report.append(f"- {r['machine'].split('#')[-1]}: {r['status']}")
    
    # 2. Sensor Performance
    report.append("\n## 2. Sensor Performance")
    results = await graph_manager.query_graph("""
        SELECT ?machine (AVG(?reading) as ?avg_reading) WHERE {
            ?sensor <http://example.org/core#attachedTo> ?machine ;
                   <http://example.org/core#latestReading> ?reading .
        }
        GROUP BY ?machine
    """)
    for r in results:
        avg_reading = float(r['avg_reading'])
        report.append(f"- {r['machine'].split('#')[-1]}: Average Reading = {avg_reading:.1f}")
    
    # 3. High Alert Sensors
    report.append("\n## 3. High Alert Sensors")
    results = await graph_manager.query_graph("""
        SELECT ?machine ?sensor ?reading ?status WHERE {
            ?sensor <http://example.org/core#attachedTo> ?machine ;
                   <http://example.org/core#latestReading> ?reading .
            ?machine <http://example.org/core#hasStatus> ?status .
            FILTER(?reading > 50)
        }
    """)
    if results:
        for r in results:
            reading = float(r['reading'])
            report.append(f"- {r['sensor'].split('#')[-1]} on {r['machine'].split('#')[-1]}: {reading:.1f} (Status: {r['status']})")
    else:
        report.append("- No high alert sensors")
    
    # 4. System Statistics
    report.append("\n## 4. System Statistics")
    validation = await graph_manager.validate_graph()
    report.append(f"- Total System Components: {validation['subjects']}")
    report.append(f"- Active Relationships: {validation['predicates']}")
    report.append(f"- Total Data Points: {validation['triple_count']}")
    
    # 5. Recommendations
    report.append("\n## 5. Key Insights & Recommendations")
    
    # Check for machines in maintenance
    maintenance_machines = [r for r in results if r['status'] == 'Maintenance']
    if maintenance_machines:
        report.append("- Maintenance Required:")
        for machine in maintenance_machines:
            report.append(f"  * {machine['machine'].split('#')[-1]} needs attention")
    
    # Check for high readings
    high_readings = await graph_manager.query_graph("""
        SELECT ?sensor ?reading WHERE {
            ?sensor <http://example.org/core#latestReading> ?reading .
            FILTER(?reading > 50)
        }
    """)
    if high_readings:
        report.append("- High Sensor Readings Detected:")
        for reading in high_readings:
            reading_value = float(reading['reading'])
            report.append(f"  * {reading['sensor'].split('#')[-1]}: {reading_value:.1f}")
    
    return "\n".join(report)

def send_email_report(report_content, to_email="ceo@example.com"):
    # Email configuration
    sender_email = "system@example.com"
    sender_password = "your_password_here"  # In production, use environment variables
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = f"Knowledge Graph Status Report - {datetime.now().strftime('%Y-%m-%d')}"
    
    # Attach report
    msg.attach(MIMEText(report_content, 'plain'))
    
    # Send email (commented out for safety)
    """
    try:
        server = smtplib.SMTP('smtp.example.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Report sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    """
    
    # For demo, just print the report
    print("\n=== CEO Report ===\n")
    print(report_content)
    print("\n=== End Report ===\n")
    print("Note: Email sending is disabled for demo. Configure SMTP settings to enable email delivery.")

if __name__ == "__main__":
    report = asyncio.run(generate_ceo_report())
    send_email_report(report) 