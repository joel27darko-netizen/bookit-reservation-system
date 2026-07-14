"""
QR code generation for booking check-in.

We encode a compact payload ("BOOKIT:<reference>") rather than a full
URL, since the simulated scanner just needs to look the booking up by
reference. In a production system this could encode a signed URL instead.
"""
import base64
import io

import qrcode


class QRService:
    @staticmethod
    def generate_qr_base64(reference: str) -> str:
        """Return a base64-encoded PNG data URI for embedding directly in <img src>."""
        payload = f"BOOKIT:{reference}"
        img = qrcode.make(payload)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    @staticmethod
    def decode_payload(payload: str) -> str:
        """Extract the booking reference from a scanned QR payload."""
        if payload.startswith("BOOKIT:"):
            return payload.split("BOOKIT:", 1)[1].strip()
        return payload.strip()
