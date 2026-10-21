"""只增不改的帳本。只有程式能寫（沒有任何修改/刪除介面）；每筆帶雜湊鏈，事後被改動可被 verify() 抓到。
AI 只會拿到唯讀的查詢結果，不會拿到這個物件的寫入方法。"""
import hashlib
import json
import threading
import time
from pathlib import Path


def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def events(self):
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def verify(self):
        """回傳 (ok, 第一筆有問題的 seq 或 None)。"""
        prev = "0" * 64
        for i, e in enumerate(self.events()):
            body = {k: v for k, v in e.items() if k != "hash"}
            if e.get("seq") != i + 1 or e.get("prev") != prev or hashlib.sha256(_canon(body).encode()).hexdigest() != e.get("hash"):
                return False, e.get("seq", i + 1)
            prev = e["hash"]
        return True, None

    def append(self, event_type, **fields):
        with self._lock:
            ok, bad = self.verify()
            if not ok:
                raise RuntimeError(f"帳本已被改動（第 {bad} 筆起不一致），拒絕再寫入")
            evs = self.events()
            prev = evs[-1]["hash"] if evs else "0" * 64
            body = {"seq": len(evs) + 1, "type": event_type, "written_at": fields.pop("written_at", time.time()),
                    "prev": prev, **fields}
            body["hash"] = hashlib.sha256(_canon({k: v for k, v in body.items()}).encode()).hexdigest()
            with self.path.open("a", encoding="utf-8") as f:
                f.write(_canon(body) + "\n")
            return body
