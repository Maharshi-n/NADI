import os
import sys
import random
import time
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add API directory to sys.path to import db
api_path = '/app' if os.path.exists('/app/db.py') else os.path.join(os.path.dirname(__file__), '../../apps/api')
sys.path.insert(0, api_path)
from db import SyncSessionLocal

def run_federation_simulation(db_session=None):
    """
    Simulate a Federated Learning process (FedProx) across 5 state clients.
    Writes the simulated rounds to the `fl_rounds` table and clients to `fl_clients`.
    """
    if db_session is None:
        session = SyncSessionLocal()
    else:
        session = db_session
        
    try:
        # 1. Clear existing FL data to reset the demo
        session.execute(text("DELETE FROM fl_rounds"))
        session.execute(text("DELETE FROM fl_clients"))
        session.commit()
        
        # 2. Setup the 5 simulated state clients
        states = [
            {"name": "Madhya Pradesh", "samples": 4200, "status": "Training"},
            {"name": "Maharashtra", "samples": 5800, "status": "Training"},
            {"name": "Gujarat", "samples": 3900, "status": "Training"},
            {"name": "Rajasthan", "samples": 4500, "status": "Training"},
            {"name": "Chhattisgarh", "samples": 120, "status": "Cold-Start Transferring"}, # Cold start
        ]
        
        for state in states:
            session.execute(text("""
                INSERT INTO fl_clients (state_name, sample_count, last_round, model_version, status)
                VALUES (:state_name, :sample_count, 0, 'v1.0.0', :status)
            """), {
                "state_name": state["name"],
                "sample_count": state["samples"],
                "status": state["status"]
            })
        
        session.commit()

        # 3. Simulate 10 rounds of training
        baseline_acc = 0.65
        fed_acc = 0.65
        
        for round_no in range(1, 11):
            # Model accuracy curves
            # Single-state baseline flattens out faster
            baseline_acc += (0.85 - baseline_acc) * 0.15 + random.uniform(-0.02, 0.02)
            # Federated keeps climbing and surpasses baseline
            fed_acc += (0.94 - fed_acc) * 0.25 + random.uniform(-0.01, 0.02)
            
            # Simulated tensors and bytes
            tensor_count = 24  # Assuming a small encoder network
            bytes_transferred = tensor_count * 1024 * random.uniform(1.8, 2.2) # ~50KB per round
            
            session.execute(text("""
                INSERT INTO fl_rounds (
                    round_no, started_at, completed_at, aggregation_method,
                    clients_participating, bytes_transferred, tensor_count,
                    global_accuracy, baseline_accuracy,
                    patient_records_transferred, stock_rows_transferred
                ) VALUES (
                    :round_no, now() - interval '1 minute', now(), 'FedProx',
                    5, :bytes_transferred, :tensor_count,
                    :global_accuracy, :baseline_accuracy,
                    0, 0
                )
            """), {
                "round_no": round_no,
                "bytes_transferred": int(bytes_transferred),
                "tensor_count": tensor_count,
                "global_accuracy": min(1.0, fed_acc),
                "baseline_accuracy": min(1.0, baseline_acc)
            })
            
            # Update clients
            session.execute(text("""
                UPDATE fl_clients SET last_round = :round_no, status = 'Idle' WHERE state_name != 'Chhattisgarh'
            """), {"round_no": round_no})
            
            # Cold start state completes transfer at round 5
            if round_no >= 5:
                session.execute(text("""
                    UPDATE fl_clients SET last_round = :round_no, status = 'Idle' WHERE state_name = 'Chhattisgarh'
                """), {"round_no": round_no})
            
            session.commit()
            
    except Exception as e:
        session.rollback()
        print(f"Federation simulation failed: {e}")
    finally:
        if db_session is None:
            session.close()

if __name__ == "__main__":
    print("Starting federation simulation...")
    run_federation_simulation()
    print("Simulation complete.")
