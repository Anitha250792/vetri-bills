"""Expo push notifications (mobile). Failures are logged, never raised: a failed push
must not break a sale or a stock update."""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from accounts.models import DeviceToken

log = logging.getLogger(__name__)

TOKEN_PREFIXES = ("ExponentPushToken[", "ExpoPushToken[")


def send_to_users(users, title, body, data=None):
    """Send one push to every device of the given users. Returns how many were accepted."""
    if not settings.PUSH_ENABLED:
        return 0
    tokens = list(DeviceToken.objects.filter(user__in=users).values_list("token", flat=True))
    tokens = [t for t in tokens if t.startswith(TOKEN_PREFIXES)]
    if not tokens:
        return 0

    sent = 0
    for start in range(0, len(tokens), 100):  # Expo accepts 100 messages per request
        chunk = tokens[start:start + 100]
        messages = [
            {"to": t, "title": title, "body": body, "data": data or {}, "sound": "default"} for t in chunk
        ]
        request = urllib.request.Request(
            settings.EXPO_PUSH_URL,
            data=json.dumps(messages).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                tickets = json.loads(response.read()).get("data", [])
        except (urllib.error.URLError, OSError, ValueError) as exc:
            log.warning("Expo push failed: %s", exc)
            continue

        dead = []
        for token, ticket in zip(chunk, tickets):
            if ticket.get("status") == "ok":
                sent += 1
            elif (ticket.get("details") or {}).get("error") == "DeviceNotRegistered":
                dead.append(token)  # app uninstalled: stop sending to this token
        if dead:
            DeviceToken.objects.filter(token__in=dead).delete()
    return sent
