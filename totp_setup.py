"""Set up the two-factor unlock for CloudLap.

  python totp_setup.py --show-qr      create a secret if none exists and show a QR code
                                      in a window (nothing is written to disk but config.json)
  python totp_setup.py --check 123456 test a code from the authenticator app
  python totp_setup.py --new --show-qr  replace the secret (old authenticator entry stops working)

The secret is stored as "totp_secret" in config.json (git-ignored). It is never printed.
Needs `pip install qrcode pillow` only for --show-qr.
"""

import json
import socket
import sys
from pathlib import Path

import totp

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def ensure_secret(force_new: bool = False) -> str:
    cfg = load_config()
    if force_new or not cfg.get("totp_secret"):
        cfg["totp_secret"] = totp.new_secret()
        save_config(cfg)
        print("New secret saved to config.json.")
    return cfg["totp_secret"]


def show_qr(secret: str) -> None:
    import tkinter as tk

    import qrcode
    from PIL import ImageTk

    uri = totp.otpauth_uri(secret, socket.gethostname())
    img = qrcode.make(uri).convert("RGB").resize((420, 420))
    root = tk.Tk()
    root.title("CloudLap - scan with your authenticator app")
    root.attributes("-topmost", True)
    photo = ImageTk.PhotoImage(img)
    tk.Label(root, image=photo).pack(padx=16, pady=(16, 8))
    tk.Label(root, text="Scan in Google or Microsoft Authenticator.\nClose this window when done.").pack()
    tk.Button(root, text="Close", command=root.destroy).pack(pady=12)
    root.mainloop()


def main(argv: list) -> int:
    if "--check" in argv:
        i = argv.index("--check")
        code = argv[i + 1] if i + 1 < len(argv) else ""
        secret = load_config().get("totp_secret")
        if not secret:
            print("No secret configured.")
            return 2
        ok = totp.verify(secret, code) is not None
        print("Code OK." if ok else "Code NOT valid.")
        return 0 if ok else 1
    if "--show-qr" in argv:
        show_qr(ensure_secret(force_new="--new" in argv))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
