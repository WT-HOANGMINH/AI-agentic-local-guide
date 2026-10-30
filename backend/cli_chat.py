"""Thu AI trong terminal (khong can giao dien):  python -m backend.cli_chat"""
from backend.database import SessionLocal
from backend.services.dialogue import State, respond
from backend.services.intent_service import predict_intent

st = State()
print("DaNang Guide (tu huan luyen). Go 'exit' de thoat.")
while True:
    msg = input("\nBan: ").strip()
    if msg.lower() in {"exit", "quit"}:
        break
    if not msg:
        continue
    pred = predict_intent(msg)
    db = SessionLocal()
    try:
        r = respond(st, msg, pred["intent"], pred["confidence"], db)
    finally:
        db.close()
    for s in r["steps"]:
        print("  .", s)
    print("AI:", r["text"])
