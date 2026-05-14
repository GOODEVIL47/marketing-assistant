import os


def _load_config():
    return {
        "enabled": os.getenv("SEND_EMAIL", "false").strip().lower() == "true",
        "provider": os.getenv("EMAIL_PROVIDER", "resend").strip().lower(),
        "api_key": os.getenv("RESEND_API_KEY", "").strip(),
        "email_from": os.getenv("EMAIL_FROM", "").strip(),
        "email_to": os.getenv("EMAIL_TO", "").strip(),
    }


def _missing_vars(config):
    required = {
        "RESEND_API_KEY": config["api_key"],
        "EMAIL_FROM": config["email_from"],
        "EMAIL_TO": config["email_to"],
    }
    return [name for name, val in required.items() if not val]


def _send_via_resend(config, subject, html_body, text_body):
    try:
        import resend
    except ImportError:
        print("The 'resend' package is not installed. Run: pip install resend")
        return False

    resend.api_key = config["api_key"]

    print("[EMAIL DEBUG] Payload has html:", "yes" if html_body else "NO — EMPTY")
    print("[EMAIL DEBUG] Payload has text:", "yes" if text_body else "NO — EMPTY")
    print("[EMAIL DEBUG] HTML length:", len(html_body))
    print("[EMAIL DEBUG] Text length:", len(text_body))

    if not html_body or not html_body.lstrip().startswith("<!"):
        print("[EMAIL DEBUG] WARNING: html_body does not start with <!DOCTYPE — may not render as HTML")
        print("[EMAIL DEBUG] html_body preview:", repr(html_body[:120]))

    params: resend.Emails.SendParams = {
        "from": config["email_from"],
        "to": [config["email_to"]],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    print("[EMAIL DEBUG] Params keys being sent:", list(params.keys()))

    try:
        response = resend.Emails.send(params)
        email_id = response["id"]
        print(f"Email sent successfully. Resend ID: {email_id}")
        return True
    except Exception as e:
        print(f"Resend error: {e}")
        print("Digest was saved locally. Email was not sent.")
        return False


def send_digest(subject, html_body, text_body):
    """
    Send the digest by email if SEND_EMAIL=true.

    Returns True if sent, False if skipped or failed.
    Digest generation is never blocked by email errors.
    """
    config = _load_config()

    if not config["enabled"]:
        print("Email disabled. Digest saved locally.")
        return False

    missing = _missing_vars(config)
    if missing:
        print(
            f"Email enabled (SEND_EMAIL=true) but missing required variable(s): "
            f"{', '.join(missing)}"
        )
        print("Add them to your .env file. Digest saved locally.")
        return False

    provider = config["provider"]
    if provider != "resend":
        print(
            f"Unknown email provider: '{provider}'. "
            "Only 'resend' is currently supported. Digest saved locally."
        )
        return False

    return _send_via_resend(config, subject, html_body, text_body)
