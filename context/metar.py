"""METAR / airport station observations -- optional third reference, restricted subset.

Only for flights close enough to a station. METAR is measured at 10 m over a runway,
in terrain that is open and flat by construction, so it is comparable only under
restricted conditions and those conditions must be stated with the result.

**Scope constraint:** this lives inside the M4 budget. If it does not fit, it is cut.
It does not become its own milestone.

Blocked on: C8 in docs/01-source-audit.md (which archive, under which terms).
"""
