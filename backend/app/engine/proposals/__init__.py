"""Machine proposals from a language model (Product 0.16 AP1, AP-D1–AP-D11).

One provider interface serves every feature: a feature builds its context through
``context.py`` (the only code that reads data for a provider, held to the send level), asks through
``calls.ask`` (the only code that calls a provider; it checks the answer's shape and records the
call) and turns the answer into steps or changes the person edits. A proposal never writes live
data, and a provider that fails or answers out of shape is a warning: deterministic results stand.
"""
