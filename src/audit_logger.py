import hashlib
import json
import datetime

class CryptographicAuditLogger:
    def __init__(self, log_filepath="src/audit_ledger.json"):
        self.log_filepath = log_filepath
        self.ledger = []
        self._load_or_init_ledger()

    def _load_or_init_ledger(self):
        try:
            with open(self.log_filepath, "r") as f:
                self.ledger = json.load(f)
                print(f"Loaded existing audit ledger with {len(self.ledger)} entries.")
        except FileNotFoundError:
            # Initialize with standard genesis block
            genesis_entry = self._create_entry("GENESIS_BLOCK", "0", {"message": "Audit Ledger Initialized"})
            self.ledger = [genesis_entry]
            self._write_ledger()
            print("Initialized genesis block for cryptographic audit ledger.")

    def _create_entry(self, event_type, prev_hash, payload):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        serialized_payload = json.dumps(payload, sort_keys=True)
        
        # Hash component calculation
        raw_data = f"{event_type}|{prev_hash}|{timestamp}|{serialized_payload}"
        entry_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
        
        return {
            "event_type": event_type,
            "previous_hash": prev_hash,
            "timestamp": timestamp,
            "payload": payload,
            "hash": entry_hash
        }

    def log_event(self, event_type, payload):
        prev_hash = self.ledger[-1]["hash"]
        new_entry = self._create_entry(event_type, prev_hash, payload)
        self.ledger.append(new_entry)
        self._write_ledger()
        return new_entry["hash"]

    def verify_ledger_integrity(self):
        """
        Validates the integrity of the audit ledger by verifying chained hashes.
        """
        for i in range(1, len(self.ledger)):
            prev_entry = self.ledger[i-1]
            curr_entry = self.ledger[i]
            
            if curr_entry["previous_hash"] != prev_entry["hash"]:
                return False, f"Integrity broken at entry index {i}: Block mismatch!"
            
            # Recalculate and assert local block hash matches expected hash 
            serialized_payload = json.dumps(curr_entry["payload"], sort_keys=True)
            raw_data = f"{curr_entry['event_type']}|{curr_entry['previous_hash']}|{curr_entry['timestamp']}|{serialized_payload}"
            recalc_hash = hashlib.sha256(raw_data.encode('utf-8')).hexdigest()
            if recalc_hash != curr_entry["hash"]:
                return False, f"Integrity broken at entry index {i}: Modified content hash!"
                
        return True, "Ledger integrity verified successfully (All chained hashes match)."

    def _write_ledger(self):
        with open(self.log_filepath, "w") as f:
            json.dump(self.ledger, f, indent=2)
