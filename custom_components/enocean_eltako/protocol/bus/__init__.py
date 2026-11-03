"""Eltako RS485 bus of the series 14: what can be read from it without writing to it.

Only what Eltako publishes is implemented (see observe.py and docs/mockups/eltako-bus-konzept.md,
"Phase 3: Quellenlage"). The PCT14 protocol of the FAM14 (device list, memory read, base ID
read) is not published; nothing here sends a telegram to the FAM14 or to a bus device.
"""
