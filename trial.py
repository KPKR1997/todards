
import json
import smtplib
import ssl
from pathlib import Path

CONFIG_PATH = Path("notifications/email_settings.json")

def test_email_connection():
    if not CONFIG_PATH.exists():
        print(f"ERROR: {CONFIG_PATH.resolve()} not found")
        return

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)["email_settings"]

    host = config["smtp_host"]
    port = int(config["smtp_port"])
    username = config["username"]
    password = config["password"]
    use_tls = config.get("use_tls", True)

    print(f"SMTP server: {host}:{port}")
    print(f"TLS enabled: {use_tls}")
    print(f"Username configured: {bool(username)}")
    print(f"Password configured: {bool(password)}")

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            print("\n[1/3] Connecting...")
            code, message = server.ehlo()
            print(f"EHLO: {code} {message.decode(errors='replace')}")

            if use_tls:
                print("\n[2/3] Starting TLS...")
                server.starttls(context=ssl.create_default_context())
                code, message = server.ehlo()
                print(f"TLS successful; EHLO: {code}")

            print("\n[3/3] Authenticating...")
            server.login(username, password)
            print("SUCCESS: SMTP authentication passed.")

    except smtplib.SMTPAuthenticationError as e:
        print(f"AUTHENTICATION FAILED: {e.smtp_code} {e.smtp_error!r}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SERVER DISCONNECTED: {e}")
    except (OSError, smtplib.SMTPException) as e:
        print(f"SMTP ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_email_connection()
