"""Host names that mean this computer, as every address check of the engine reads them."""

# The names a URL may use for this computer. The webhook, sign-in provider, assistant registration
# and mail service address checks all read this one set; a check of an address a name resolved to
# (``ipaddress.is_loopback``, any 127.x.x.x) is a different question and stays where it is asked.
LOOPBACK = frozenset({"localhost", "127.0.0.1", "::1"})
