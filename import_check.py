
import sys
import os

# Add the User project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../User")))

from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../User/.env"))
load_dotenv(env_path)

print("Attempting to import Ticket and Status...")
try:
    from backend.app.entities.tickets import Ticket, Status, Priority
    print("Import successful!")
    print(f"Status members: {[s.value for s in Status]}")
    print(f"Priority members: {[p.value for p in Priority]}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
