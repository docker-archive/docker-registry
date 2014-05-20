# -*- coding: utf-8 -*-

import blinker


_signals = blinker.Namespace()

# Triggered when a repository is modified (registry/index.py)
repository_created = _signals.signal('repository-created')
repository_updated = _signals.signal('repository-updated')
repository_deleted = _signals.signal('repository-deleted')

# Triggered when a tag is modified (registry/tags.py)
tag_created = _signals.signal('tag-created')
tag_deleted = _signals.signal('tag-deleted')
