"""Generate a VAPID keypair for Web Push.

    python manage.py generate_vapid_keys

Prints the two env vars to paste into your .env. The public key is the
P-256 uncompressed point (what the browser's applicationServerKey expects);
the private key is the raw 32-byte scalar, both base64url (no padding) — the
format py_vapid / pywebpush accept directly.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Generate a VAPID keypair for Web Push and print the env vars."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_raw = private_key.private_numbers().private_value.to_bytes(32, "big")
        public_raw = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )

        self.stdout.write(self.style.SUCCESS("VAPID keys generated — add to .env:\n"))
        self.stdout.write(f"VAPID_PUBLIC_KEY={_b64url(public_raw)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={_b64url(private_raw)}")
        self.stdout.write("VAPID_SUBJECT=mailto:admin@yourdomain.com")
