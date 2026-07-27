"""Governance for Metasploit-class MCP tools.

Metasploit MCP servers are treated as a hostile-capability dependency: RIF
must prove it can distinguish security *knowledge* from security *authority*,
constrain what a tool may do, explain why, and refuse escalation. Nothing in
this package executes Metasploit modules or reaches a live RPC endpoint; it is
the policy boundary that sits in front of one.
"""
