from services.orchestrator.db.neo4j_writer import Neo4jWriter
from datetime import datetime

def test():
    writer = Neo4jWriter()
    print("Testing Neo4jWriter...")
    writer.ensure_constraints()
    print("Constraints ensured!")

    signals = [
        type('Signal', (object,), {
            'id': 'signal-1',
            'company_name': 'Acme Corp',
            'title': 'Hiring Engineers',
            'url': 'https://acme.com/jobs'
        })()
    ]

    writer.merge_signals(signals)
    print("Signals merged successfully!")

if __name__ == "__main__":
    test()
