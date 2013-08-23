
import blinker


_signals = blinker.Namespace()

# Triggered when a tag is modified (registry/tags.py)
tag_created = _signals.signal('tag-created')
tag_deleted = _signals.signal('tag-deleted')
